#!/usr/bin/env python3
"""Derive Concho County Commissioner precincts from official current sources."""
from __future__ import annotations
import argparse, hashlib, json, shutil, time, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any
import fitz, shapefile
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

MAP_URL="https://www.co.concho.tx.us/upload/page/6097/County%20Precinct%20Map_11222023102640.PDF"
TLC_URL="https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip"
MAP_SHA="eb8f1e9f94431328b64188496354753c4ffb78b59b175e64192237f778bfc843"
TLC_SHA="70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
EXPECTED_IDS=["101","102","203","204","205","306","407","408"]
EXPECTED_ASSIGNMENTS={value:value[0] for value in EXPECTED_IDS}
COUNTY_FIPS="95";COUNTY_NAME="concho"
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"

def dump(path:Path,value:Any)->None:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()
def download(url:str,path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(1,6):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
            with urllib.request.urlopen(req,timeout=180) as src,path.open("wb") as dst:shutil.copyfileobj(src,dst,1<<20)
            if path.stat().st_size:return
        except Exception:
            path.unlink(missing_ok=True)
            if attempt==5:raise
            time.sleep(attempt*5)
def repair(g):
    if g.is_empty or g.is_valid:return g
    try:
        from shapely.validation import make_valid
        g=make_valid(g)
    except ImportError:g=g.buffer(0)
    if g.geom_type=="GeometryCollection":g=unary_union([p for p in g.geoms if p.geom_type in {"Polygon","MultiPolygon"}])
    return g
def code(value:Any)->str:
    text=str(value or "").strip()
    if text.endswith(".0"):text=text[:-2]
    return text.lstrip("0") or "0"
def pick(fields:list[str],*names:str)->str|None:
    lookup={f.casefold():f for f in fields}
    return next((lookup[n.casefold()] for n in names if n.casefold() in lookup),None)
def rounded(value:Any):
    if isinstance(value,float):return round(value,7)
    if isinstance(value,(list,tuple)):return [rounded(v) for v in value]
    if isinstance(value,dict):return {k:rounded(v) for k,v in value.items()}
    return value

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--retrieved-at",required=True);p.add_argument("--work-dir",type=Path,required=True);p.add_argument("--raw-output",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--contract-output",type=Path,required=True);p.add_argument("--evidence-output",type=Path,required=True);a=p.parse_args();a.work_dir.mkdir(parents=True,exist_ok=True)
    pdf=a.work_dir/"official-commissioner-map.pdf";z=a.work_dir/"precincts26p.zip";download(MAP_URL,pdf);download(TLC_URL,z)
    if digest(pdf)!=MAP_SHA:raise ValueError(f"Official Concho map changed: {digest(pdf)}")
    if digest(z)!=TLC_SHA:raise ValueError(f"TLC source changed: {digest(z)}")
    doc=fitz.open(pdf)
    if len(doc)!=1:raise ValueError(f"Concho map page count changed: {len(doc)}")
    extract=a.work_dir/"precincts";shutil.rmtree(extract,ignore_errors=True);extract.mkdir(parents=True)
    with zipfile.ZipFile(z) as archive:archive.extractall(extract)
    shps=list(extract.rglob("*.shp"))
    if len(shps)!=1:raise ValueError(shps)
    shp=shps[0];reader=shapefile.Reader(str(shp));fields=[f[0] for f in reader.fields[1:]];fips=pick(fields,"FIPS","CNTY","COUNTYFP","COUNTY_FIP");county=pick(fields,"COUNTY","COUNTYNAME","CNTYNAME","NAME");prec=pick(fields,"PREC","PRECINCT","PCT","PCTKEY","VTD","CNTYVTD")
    if not prec or not (fips or county):raise ValueError(fields)
    crs=CRS.from_wkt(shp.with_suffix(".prj").read_text(encoding="utf-8",errors="replace"));to4326=Transformer.from_crs(crs,"EPSG:4326",always_xy=True).transform
    rows=[]
    for sr in reader.iterShapeRecords():
        attrs=dict(zip(fields,sr.record));match=bool(fips and code(attrs.get(fips))==COUNTY_FIPS) or bool(county and str(attrs.get(county) or "").strip().casefold()==COUNTY_NAME)
        if not match:continue
        pid=code(attrs.get(prec));g=repair(transform(to4326,shape(sr.shape.__geo_interface__)));rows.append({"id":pid,"attrs":attrs,"geometry":g})
    ids=sorted([r["id"] for r in rows],key=int)
    if ids!=EXPECTED_IDS:raise ValueError(f"Concho voting precincts changed: {ids}")
    groups=defaultdict(list)
    for row in rows:groups[EXPECTED_ASSIGNMENTS[row["id"]]].append(row)
    raw=[];canonical=[];geoms=[];summary={}
    for district in ("1","2","3","4"):
        source_rows=groups[district];g=repair(unary_union([r["geometry"] for r in source_rows]));geoms.append(g);source_ids=sorted([r["id"] for r in source_rows],key=int)
        props={"commissioner_precinct":district,"source_voting_precinct_count":len(source_ids),"source_voting_precinct_ids":source_ids,"identity_rule":"first digit of current three-digit voting precinct ID","official_map_sha256":MAP_SHA,"tlc_precinct_zip_sha256":TLC_SHA}
        geom=rounded(mapping(g));raw.append({"type":"Feature","properties":props,"geometry":geom});canonical.append({"type":"Feature","properties":{"geometry_id":f"concho-county-commissioner-precinct-{district}","record_id":f"TX:county:concho:commissioner_precinct:{district}","jurisdiction_name":"Concho County","district_type":"commissioner_precinct","district_id":district,"district_name":f"Commissioner Precinct {district}","source_agency":"Concho County and Texas Legislative Council","source_layer":TLC_URL,"source_request_url":TLC_URL,"source_retrieved_at":a.retrieved_at,"source_district_field":"voting_precinct_id_hundreds_digit","source_attributes":props},"geometry":geom});summary[district]=source_ids
    union_source=repair(unary_union([r["geometry"] for r in rows]));union_output=repair(unary_union(geoms));difference=union_output.symmetric_difference(union_source).area;overlap=sum(geoms[i].intersection(geoms[j]).area for i in range(4) for j in range(i+1,4))
    if difference!=0 or overlap!=0:raise ValueError({"difference":difference,"overlap":overlap})
    dump(a.raw_output,{"type":"FeatureCollection","features":raw});dump(a.output,{"type":"FeatureCollection","features":canonical})
    contract={"county":"Concho County","county_fips":COUNTY_FIPS,"official_map_url":MAP_URL,"official_map_sha256":MAP_SHA,"official_map_page_count":1,"tlc_precinct_url":TLC_URL,"tlc_precinct_zip_sha256":TLC_SHA,"voting_precinct_ids":EXPECTED_IDS,"commissioner_assignments":EXPECTED_ASSIGNMENTS,"commissioner_source_voting_precinct_ids":summary,"voting_precinct_count":8,"commissioner_precinct_count":4,"identity_method":"The county's official map labels current VTDs 101, 102, 203, 204, 205, 306, 407, and 408 inside Commissioner Precincts 1-4; the hundreds digit is the Commissioner precinct number.","interdistrict_overlap_area_degrees":round(overlap,12),"union_symmetric_difference_area_degrees":round(difference,12),"all_voting_precincts_assigned":True}
    dump(a.contract_output,contract);dump(a.evidence_output,{"contract":contract,"raw_output_sha256":digest(a.raw_output),"canonical_output_sha256":digest(a.output)})
    print(json.dumps({"voting_precincts_assigned":8,"commissioner_precincts":4,"assignments":summary,"overlap":overlap,"union_difference":difference},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
