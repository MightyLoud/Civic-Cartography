#!/usr/bin/env python3
"""Derive Ellis County Commissioner precincts from official current sources."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, time, urllib.parse, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any
import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

PORTAL="https://maps.co.ellis.tx.us/portal"
WEB_MAP_ITEM_ID="05e4901568c044819986934e3715b292"
MAP_SERVICE_ITEM_ID="484f13cc3dc64f20a64f5528ef79e035"
LAYER_URL="https://maps.co.ellis.tx.us/arcgis/rest/services/Commissioner/Commissioner_Web_Map/MapServer/680"
LAYER_NAME="Commissioner Precincts (2023-2032)"
REDISTRICTING_URL="https://www.elliscountytx.gov/1072/Redistricting-Maps-20212025"
TLC_URL="https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip"
TLC_SHA="70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
COUNTY_FIPS="139";COUNTY_NAME="ellis"
BASE_RANGES={"1":(1001,1014),"2":(1015,1026),"3":(1027,1039),"4":(1040,1059)}
SPLIT_DESCENDANTS={"1060":{"parent":"1006","district":"1"},"1061":{"parent":"1038","district":"3"}}
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
def get_json(url:str,params:dict[str,str])->tuple[dict[str,Any],str]:
    full=url+"?"+urllib.parse.urlencode(params)
    for attempt in range(1,6):
        try:
            req=urllib.request.Request(full,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
            with urllib.request.urlopen(req,timeout=120) as response:payload=json.load(response)
            if not isinstance(payload,dict) or payload.get("error"):raise ValueError(payload)
            return payload,full
        except Exception:
            if attempt==5:raise
            time.sleep(attempt*3)
    raise RuntimeError("unreachable")
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
def sequential(start:int,end:int)->list[str]:return [str(value) for value in range(start,end+1)]
def expected_for_district(district:str)->list[str]:
    start,end=BASE_RANGES[district];ids=sequential(start,end)
    ids.extend(pid for pid,rule in SPLIT_DESCENDANTS.items() if rule["district"]==district)
    return sorted(ids,key=int)

def county_identity_contract()->tuple[dict[str,dict[str,Any]],str]:
    webmap,_=get_json(f"{PORTAL}/sharing/rest/content/items/{WEB_MAP_ITEM_ID}/data",{"f":"json"})
    refs=[]
    for operational in webmap.get("operationalLayers",[]):
        for layer in operational.get("layers",[]):
            if str(layer.get("id"))=="680":refs.append({"service_url":operational.get("url"),"title":layer.get("name") or (layer.get("popupInfo") or {}).get("title")})
    if len(refs)!=1 or not str(refs[0]["service_url"]).endswith("/Commissioner_Web_Map/MapServer"):raise ValueError(refs)
    meta,_=get_json(LAYER_URL,{"f":"json"})
    if meta.get("name")!=LAYER_NAME or meta.get("geometryType")!="esriGeometryPolygon":raise ValueError({"name":meta.get("name"),"geometryType":meta.get("geometryType")})
    query,request_url=get_json(LAYER_URL+"/query",{"where":"1=1","outFields":"*","returnGeometry":"false","f":"json"})
    features=query.get("features")
    if not isinstance(features,list) or len(features)!=4:raise ValueError(f"Expected four identity rows, found {len(features or [])}")
    result={}
    for feature in features:
        attrs=feature.get("attributes") or {};district=code(attrs.get("Commissioner_Pct"));range_text=str(attrs.get("Election_Pct_Range") or "");match=re.fullmatch(r"(\d{4})-(\d{4})",range_text)
        if district not in BASE_RANGES or not match:raise ValueError(attrs)
        observed=(int(match.group(1)),int(match.group(2)))
        if observed!=BASE_RANGES[district] or attrs.get("Source")!="2021 Redistricting":raise ValueError({district:attrs})
        result[district]=attrs
    if set(result)!={"1","2","3","4"}:raise ValueError(result)
    return result,request_url

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--retrieved-at",required=True);p.add_argument("--work-dir",type=Path,required=True);p.add_argument("--raw-output",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--contract-output",type=Path,required=True);p.add_argument("--evidence-output",type=Path,required=True);a=p.parse_args();a.work_dir.mkdir(parents=True,exist_ok=True)
    identity_rows,identity_request=county_identity_contract();z=a.work_dir/"precincts26p.zip";download(TLC_URL,z)
    if digest(z)!=TLC_SHA:raise ValueError(f"TLC source changed: {digest(z)}")
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
        if match:rows.append({"id":code(attrs.get(prec)),"attrs":attrs,"geometry":repair(transform(to4326,shape(sr.shape.__geo_interface__)))})
    ids=sorted([r["id"] for r in rows],key=int);expected=sequential(1001,1061)
    if ids!=expected:raise ValueError(f"Ellis voting precincts changed: expected {expected}, found {ids}")
    groups=defaultdict(list)
    for row in rows:
        pid=row["id"]
        if pid in SPLIT_DESCENDANTS:district=SPLIT_DESCENDANTS[pid]["district"]
        else:
            number=int(pid);matches=[d for d,(start,end) in BASE_RANGES.items() if start<=number<=end]
            if len(matches)!=1:raise ValueError({pid:matches})
            district=matches[0]
        groups[district].append(row)
    raw=[];canonical=[];geoms=[];summary={}
    for district in ("1","2","3","4"):
        source_rows=groups[district];source_ids=sorted([r["id"] for r in source_rows],key=int)
        if source_ids!=expected_for_district(district):raise ValueError({district:source_ids})
        g=repair(unary_union([r["geometry"] for r in source_rows]));geoms.append(g);identity=identity_rows[district]
        descendants={pid:rule for pid,rule in SPLIT_DESCENDANTS.items() if rule["district"]==district}
        props={"commissioner_precinct":district,"base_election_precinct_range":identity["Election_Pct_Range"],"source_voting_precinct_count":len(source_ids),"source_voting_precinct_ids":source_ids,"2025_split_descendants":descendants,"identity_rule":"Ellis County GIS layer 680 ranges plus official 2025 parent-child precinct splits","county_layer_attributes":identity,"tlc_precinct_zip_sha256":TLC_SHA}
        geom=rounded(mapping(g));raw.append({"type":"Feature","properties":props,"geometry":geom});canonical.append({"type":"Feature","properties":{"geometry_id":f"ellis-county-commissioner-precinct-{district}","record_id":f"TX:county:ellis:commissioner_precinct:{district}","jurisdiction_name":"Ellis County","district_type":"commissioner_precinct","district_id":district,"district_name":f"Commissioner Precinct {district}","source_agency":"Ellis County GIS and Texas Legislative Council","source_layer":TLC_URL,"source_request_url":identity_request,"source_retrieved_at":a.retrieved_at,"source_district_field":"Commissioner_Pct, Election_Pct_Range, and 2025 split parentage","source_attributes":props},"geometry":geom});summary[district]=source_ids
    union_source=repair(unary_union([r["geometry"] for r in rows]));union_output=repair(unary_union(geoms));difference=union_output.symmetric_difference(union_source).area;overlap=sum(geoms[i].intersection(geoms[j]).area for i in range(4) for j in range(i+1,4))
    if difference!=0 or overlap!=0:raise ValueError({"difference":difference,"overlap":overlap})
    dump(a.raw_output,{"type":"FeatureCollection","features":raw});dump(a.output,{"type":"FeatureCollection","features":canonical})
    contract={"county":"Ellis County","county_fips":COUNTY_FIPS,"county_portal_url":PORTAL,"web_map_item_id":WEB_MAP_ITEM_ID,"map_service_item_id":MAP_SERVICE_ITEM_ID,"commissioner_identity_layer_url":LAYER_URL,"commissioner_identity_layer_name":LAYER_NAME,"commissioner_identity_request_url":identity_request,"district_field":"Commissioner_Pct","election_precinct_range_field":"Election_Pct_Range","base_commissioner_ranges":{d:f"{s}-{e}" for d,(s,e) in BASE_RANGES.items()},"election_precinct_split_authority_url":REDISTRICTING_URL,"split_descendants":SPLIT_DESCENDANTS,"split_accepted_at":"2025-04-15","split_effective_at":"2026-01-01","tlc_precinct_url":TLC_URL,"tlc_precinct_zip_sha256":TLC_SHA,"voting_precinct_ids":expected,"commissioner_source_voting_precinct_ids":summary,"voting_precinct_count":61,"commissioner_precinct_count":4,"identity_method":"Ellis County GIS layer 680 controls the 2021 base ranges. Official 2025 splits created 1060 from 1006 and 1061 from 1038, inheriting their parent Commissioner precincts. Current TLC polygons control exact geometry.","commissioner_adopted_at":"2021-11-30","commissioner_effective_at":"2023-01-01","interdistrict_overlap_area_degrees":round(overlap,12),"union_symmetric_difference_area_degrees":round(difference,12),"all_voting_precincts_assigned":True}
    dump(a.contract_output,contract);dump(a.evidence_output,{"contract":contract,"county_identity_rows":identity_rows,"raw_output_sha256":digest(a.raw_output),"canonical_output_sha256":digest(a.output)})
    print(json.dumps({"voting_precincts_assigned":61,"commissioner_precincts":4,"assignments":{d:[ids[0],ids[-1],len(ids)] for d,ids in summary.items()},"overlap":overlap,"union_difference":difference},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
