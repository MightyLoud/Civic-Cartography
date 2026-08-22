#!/usr/bin/env python3
"""Derive Presidio County Commissioner precincts from official ballots and TLC polygons."""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, time, urllib.request, zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any
import fitz, shapefile
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union
BASE="https://www.co.presidio.tx.us/upload/page/4732"
GENERAL_URL=f"{BASE}/2024/november_2024_general_election_sample_ballotskj.pdf"
PRIMARY_URLS={p:f"{BASE}/2026/Precinct%20{p}%20Sample%20Ballot%20Dem%20Primary.pdf" for p in ("3","4","7")}
TLC_URL="https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip"
GENERAL_SHA="cf2df87c7794947e8f71f336780de3d18746a7797fc03e145b5869094bc60cf1"
PRIMARY_SHA={"3":"948cf42286ce9e00be3c150ce37abee112a072b498fe70fcf45b61ee97a4f128","4":"8e0c4466be7331f9acac9e463d786aa090254dc0819c073a0123138df95f8529","7":"f7c4d478f5352b0a0be1f6e0028ad7e1aaa0184869e9d0512dc65e6a169b5661"}
TLC_SHA="70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
EXPECTED_IDS=["1","2","3","4","5","6","7"]
ASSIGN={"1":"1","2":"1","3":"2","4":"2","5":"3","6":"3","7":"4"}
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
def dump(path:Path,value:Any):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
def digest(path:Path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def download(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(1,6):
  try:
   req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
   with urllib.request.urlopen(req,timeout=180) as src,path.open("wb") as dst:shutil.copyfileobj(src,dst,1<<20)
   if path.stat().st_size:return
  except Exception:
   path.unlink(missing_ok=True)
   if attempt==5:raise
   time.sleep(attempt*4)
def repair(g):
 if g.is_empty or g.is_valid:return g
 try:
  from shapely.validation import make_valid
  g=make_valid(g)
 except ImportError:g=g.buffer(0)
 if g.geom_type=="GeometryCollection":g=unary_union([p for p in g.geoms if p.geom_type in {"Polygon","MultiPolygon"}])
 return g
def code(v):
 s=str(v or "").strip()
 if s.endswith(".0"):s=s[:-2]
 return s.lstrip("0") or "0"
def pick(fields,*names):
 lookup={f.casefold():f for f in fields};return next((lookup[n.casefold()] for n in names if n.casefold() in lookup),None)
def rounded(v):
 if isinstance(v,float):return round(v,7)
 if isinstance(v,(list,tuple)):return [rounded(x) for x in v]
 if isinstance(v,dict):return {k:rounded(x) for k,x in v.items()}
 return v
def pdf_text(path):return "\n".join(page.get_text() for page in fitz.open(path))
def verify_ballots(work):
 general=work/"2024-general-ballots.pdf";download(GENERAL_URL,general)
 if digest(general)!=GENERAL_SHA:raise ValueError("Presidio 2024 ballot file changed")
 body=pdf_text(general)
 for precinct,commissioner in {"1":"1","2":"1","5":"3","6":"3"}.items():
  block=re.search(rf"Precinct\s+{precinct}\b(.*?)(?=Precinct\s+{int(precinct)+1}\b|\Z)",body,re.S|re.I)
  if not block or not re.search(rf"County Commissioner,\s*Precinct No[.,]?\s*{commissioner}\b",block.group(1),re.I):raise ValueError(f"Ballot mapping missing {precinct}->{commissioner}")
 for precinct,url in PRIMARY_URLS.items():
  pdf=work/f"2026-primary-{precinct}.pdf";download(url,pdf)
  if digest(pdf)!=PRIMARY_SHA[precinct]:raise ValueError(f"Presidio precinct {precinct} ballot changed")
  m=re.search(r"County Commissioner,\s*Precinct No[.,]?\s*(\d)",pdf_text(pdf),re.I)
  if not m or m.group(1)!=ASSIGN[precinct]:raise ValueError(f"Ballot mapping changed for {precinct}")
 return {"general_ballot_url":GENERAL_URL,"general_ballot_sha256":GENERAL_SHA,"primary_ballot_urls":PRIMARY_URLS,"primary_ballot_sha256":PRIMARY_SHA}
def main():
 p=argparse.ArgumentParser();p.add_argument("--retrieved-at",required=True);p.add_argument("--work-dir",type=Path,required=True);p.add_argument("--raw-output",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--contract-output",type=Path,required=True);p.add_argument("--evidence-output",type=Path,required=True);a=p.parse_args();a.work_dir.mkdir(parents=True,exist_ok=True)
 ballot=verify_ballots(a.work_dir);z=a.work_dir/"precincts26p.zip";download(TLC_URL,z)
 if digest(z)!=TLC_SHA:raise ValueError("TLC source changed")
 extract=a.work_dir/"precincts";shutil.rmtree(extract,ignore_errors=True);extract.mkdir()
 with zipfile.ZipFile(z) as ar:ar.extractall(extract)
 shp=next(extract.rglob("*.shp"));reader=shapefile.Reader(str(shp));fields=[f[0] for f in reader.fields[1:]]
 fips=pick(fields,"FIPS","CNTY","COUNTYFP","COUNTY_FIP");county=pick(fields,"COUNTY","COUNTYNAME","CNTYNAME","NAME");prec=pick(fields,"PREC","PRECINCT","PCT","PCTKEY","VTD","CNTYVTD")
 if not prec or not(fips or county):raise ValueError(fields)
 crs=CRS.from_wkt(shp.with_suffix(".prj").read_text(encoding="utf-8",errors="replace"));to4326=Transformer.from_crs(crs,"EPSG:4326",always_xy=True).transform
 rows=[]
 for sr in reader.iterShapeRecords():
  attrs=dict(zip(fields,sr.record));match=bool(fips and code(attrs.get(fips))=="377") or bool(county and str(attrs.get(county) or "").strip().casefold()=="presidio")
  if match:rows.append({"id":code(attrs.get(prec)),"geometry":repair(transform(to4326,shape(sr.shape.__geo_interface__)))})
 ids=sorted([r["id"] for r in rows],key=int)
 if ids!=EXPECTED_IDS:raise ValueError(f"Presidio voting precincts changed: {ids}")
 groups=defaultdict(list)
 for row in rows:groups[ASSIGN[row["id"]]].append(row)
 raw=[];canonical=[];geoms=[];summary={}
 for district in ("1","2","3","4"):
  source=groups[district];g=repair(unary_union([r["geometry"] for r in source]));geoms.append(g);source_ids=sorted([r["id"] for r in source],key=int)
  props={"commissioner_precinct":district,"source_voting_precinct_count":len(source_ids),"source_voting_precinct_ids":source_ids,"identity_rule":"official county ballots identify the Commissioner precinct race for each election precinct","ballot_evidence":ballot,"tlc_precinct_zip_sha256":TLC_SHA}
  geom=rounded(mapping(g));raw.append({"type":"Feature","properties":props,"geometry":geom});canonical.append({"type":"Feature","properties":{"geometry_id":f"presidio-county-commissioner-precinct-{district}","record_id":f"TX:county:presidio:commissioner_precinct:{district}","jurisdiction_name":"Presidio County","district_type":"commissioner_precinct","district_id":district,"district_name":f"Commissioner Precinct {district}","source_agency":"Presidio County and Texas Legislative Council","source_layer":TLC_URL,"source_request_url":TLC_URL,"source_retrieved_at":a.retrieved_at,"source_district_field":"official_ballot_commissioner_assignment","source_attributes":props},"geometry":geom});summary[district]=source_ids
 union_source=repair(unary_union([r["geometry"] for r in rows]));union_output=repair(unary_union(geoms));difference=union_output.symmetric_difference(union_source).area;overlap=sum(geoms[i].intersection(geoms[j]).area for i in range(4) for j in range(i+1,4))
 if difference!=0 or overlap!=0:raise ValueError({"difference":difference,"overlap":overlap})
 dump(a.raw_output,{"type":"FeatureCollection","features":raw});dump(a.output,{"type":"FeatureCollection","features":canonical})
 contract={"county":"Presidio County","county_fips":"377","ballot_evidence":ballot,"tlc_precinct_url":TLC_URL,"tlc_precinct_zip_sha256":TLC_SHA,"voting_precinct_ids":EXPECTED_IDS,"commissioner_assignments":ASSIGN,"commissioner_source_voting_precinct_ids":summary,"voting_precinct_count":7,"commissioner_precinct_count":4,"identity_method":"Official 2024 general and 2026 primary ballots identify which Commissioner precinct race appears in each election precinct.","interdistrict_overlap_area_degrees":round(overlap,12),"union_symmetric_difference_area_degrees":round(difference,12),"all_voting_precincts_assigned":True}
 dump(a.contract_output,contract);dump(a.evidence_output,{"contract":contract,"raw_output_sha256":digest(a.raw_output),"canonical_output_sha256":digest(a.output)})
 print(json.dumps({"voting_precincts_assigned":7,"commissioner_precincts":4,"assignments":summary,"overlap":overlap,"union_difference":difference},indent=2))
if __name__=="__main__":main()
