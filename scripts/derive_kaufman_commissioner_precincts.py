#!/usr/bin/env python3
"""Derive Kaufman County Commissioner precincts from official sources."""
from __future__ import annotations
import argparse, hashlib, json, math, shutil, statistics, time, urllib.request, zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import shapefile
from PIL import Image
from pyproj import CRS, Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform, unary_union

UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
PRECINCT_URL=("https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-"
"c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip")
MAP_URL="https://www.kaufmancounty.net/ImageRepository/Document?documentId=8470"
MAP_SHA="49673d66657b8dd93daec7aad205d549023bffa263c5db71707032ae321ca8e6"
MAP_SIZE=(940,788); MAP_BBOX=(219.0,66.0,735.0,727.0)
COLORS={"1":(103,149,143),"2":(202,145,125),"3":(226,224,162),"4":(142,78,76)}
ANCHORS={"1":(650,400),"2":(250,140),"3":(650,120),"4":(400,650)}

def dump(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def download(url:str,path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(1,6):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
            with urllib.request.urlopen(req,timeout=180) as src,path.open("wb") as dst:
                shutil.copyfileobj(src,dst,1<<20)
            if path.stat().st_size: return
        except Exception:
            path.unlink(missing_ok=True)
            if attempt==5: raise
            time.sleep(attempt*5)
    raise RuntimeError(url)

def repair(g):
    if g.is_empty or g.is_valid:return g
    try:
        from shapely.validation import make_valid
        g=make_valid(g)
    except ImportError:g=g.buffer(0)
    if g.geom_type=="GeometryCollection":
        g=unary_union([p for p in g.geoms if p.geom_type in {"Polygon","MultiPolygon"}])
    return g

def pick(fields,*names):
    lookup={x.casefold():x for x in fields}
    return next((lookup[x.casefold()] for x in names if x.casefold() in lookup),None)

def code(v):
    s=str(v or "").strip()
    if s.endswith(".0"):s=s[:-2]
    return s.lstrip("0") or "0"

def load_precincts(zip_path:Path,folder:Path):
    shutil.rmtree(folder,ignore_errors=True);folder.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:z.extractall(folder)
    shp=list(folder.rglob("*.shp"))
    if len(shp)!=1:raise ValueError(f"Expected one shapefile: {shp}")
    prj=shp[0].with_suffix(".prj")
    reader=shapefile.Reader(str(shp[0]))
    fields=[x[0] for x in reader.fields[1:]]
    fips=pick(fields,"FIPS","CNTY","COUNTYFP","COUNTY_FIP")
    county=pick(fields,"COUNTY","COUNTYNAME","CNTYNAME","NAME")
    pct=pick(fields,"PREC","PRECINCT","PCT","PCTKEY","VTD","CNTYVTD")
    if not (fips or county) or not pct:raise ValueError(f"Fields not recognized: {fields}")
    crs=CRS.from_wkt(prj.read_text(encoding="utf-8",errors="replace"))
    t3857=Transformer.from_crs(crs,"EPSG:3857",always_xy=True).transform
    t4326=Transformer.from_crs(crs,"EPSG:4326",always_xy=True).transform
    rows=[]
    for sr in reader.iterShapeRecords():
        rec=dict(zip(fields,sr.record))
        match=(fips and code(rec.get(fips))=="257") or (county and str(rec.get(county) or "").strip().casefold()=="kaufman")
        if not match:continue
        g=repair(shape(sr.shape.__geo_interface__))
        if g.geom_type not in {"Polygon","MultiPolygon"}:raise ValueError(g.geom_type)
        rows.append({"id":str(rec.get(pct) or "").strip(),"g3857":repair(transform(t3857,g)),"g4326":repair(transform(t4326,g))})
    if not rows or any(not x["id"] for x in rows):raise ValueError("Kaufman precinct rows missing")
    return rows,{"shapefile":str(shp[0].relative_to(folder)),"projection_wkt":crs.to_wkt(),"fields":fields,
                 "fips_field":fips,"county_field":county,"precinct_field":pct,"voting_precinct_count":len(rows)}

def pixel(point,bounds):
    minx,miny,maxx,maxy=bounds;l,t,r,b=MAP_BBOX
    return l+(point.x-minx)/(maxx-minx)*(r-l),b-(point.y-miny)/(maxy-miny)*(b-t)

def points(g):
    out=[g.representative_point()]
    if g.contains(g.centroid):out.append(g.centroid)
    minx,miny,maxx,maxy=g.bounds
    for n in (7,11):
        for ix in range(1,n):
            for iy in range(1,n):
                p=Point(minx+(maxx-minx)*ix/n,miny+(maxy-miny)*iy/n)
                if g.contains(p):out.append(p)
        if len(out)>=25:break
    unique={(round(p.x),round(p.y)):p for p in out}
    return list(unique.values())[:64]

def patch(img,x,y):
    x=int(round(x));y=int(round(y));vals=[]
    if not(0<=x<img.width and 0<=y<img.height):return None
    for xx in range(max(0,x-2),min(img.width,x+3)):
        for yy in range(max(0,y-2),min(img.height,y+3)):
            rgb=img.getpixel((xx,yy))[:3]
            if sum(rgb)>=130 and not all(v>245 for v in rgb):vals.append(rgb)
    return tuple(int(statistics.median(v)) for v in zip(*vals)) if vals else None

def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def classify(img,g,bounds):
    obs=[]
    for p in points(g):
        xy=pixel(p,bounds);rgb=patch(img,*xy)
        if not rgb:continue
        ranked=sorted((dist(rgb,c),d) for d,c in COLORS.items())
        obs.append({"district":ranked[0][1],"distance":round(ranked[0][0],3),
                    "separation":round(ranked[1][0]-ranked[0][0],3),"pixel":[round(xy[0],2),round(xy[1],2)]})
    if not obs:raise ValueError("No color observations")
    counts=Counter(x["district"] for x in obs);district,count=counts.most_common(1)[0]
    dominant=[x for x in obs if x["district"]==district]
    return district,count/len(obs),len(obs),statistics.fmean(x["distance"] for x in dominant),min(x["separation"] for x in dominant),obs

def rounded(value):
    if isinstance(value,float):return round(value,7)
    if isinstance(value,(list,tuple)):return [rounded(x) for x in value]
    if isinstance(value,dict):return {k:rounded(v) for k,v in value.items()}
    return value

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--retrieved-at",required=True);p.add_argument("--work-dir",type=Path,required=True)
    p.add_argument("--raw-output",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--contract-output",type=Path,required=True);p.add_argument("--evidence-output",type=Path,required=True)
    p.add_argument("--precinct-url",default=PRECINCT_URL);p.add_argument("--official-map-url",default=MAP_URL);a=p.parse_args()
    a.work_dir.mkdir(parents=True,exist_ok=True);z=a.work_dir/"precincts26p.zip";m=a.work_dir/"official-map.png"
    download(a.precinct_url,z);download(a.official_map_url,m)
    zsha,msha=digest(z),digest(m)
    if msha!=MAP_SHA:raise ValueError(f"Map changed: {msha}")
    img=Image.open(m).convert("RGB")
    if img.size!=MAP_SIZE:raise ValueError(f"Map dimensions changed: {img.size}")
    rows,meta=load_precincts(z,a.work_dir/"precincts")
    union3857=repair(unary_union([x["g3857"] for x in rows]));union4326=repair(unary_union([x["g4326"] for x in rows]))
    assignments=[];groups=defaultdict(list)
    for row in rows:
        d,conf,n,mean,sep,obs=classify(img,row["g3857"],union3857.bounds)
        if conf<0.55:raise ValueError(f"Low confidence {row['id']}: {conf}")
        groups[d].append(row["g4326"]);assignments.append({"voting_precinct_id":row["id"],"commissioner_precinct":d,
            "confidence":round(conf,6),"observation_count":n,"mean_color_distance":round(mean,6),
            "minimum_color_separation":round(sep,6),"observations":obs})
    if set(groups)!={"1","2","3","4"}:raise ValueError(sorted(groups))
    raw=[];canonical=[];dissolved=[];summary={}
    for d in ("1","2","3","4"):
        g=repair(unary_union(groups[d]));dissolved.append(g)
        assigned=[x for x in assignments if x["commissioner_precinct"]==d]
        ids=sorted((x["voting_precinct_id"] for x in assigned),key=lambda v:(len(v),v));cs=[x["confidence"] for x in assigned]
        attrs={"commissioner_precinct":d,"source_voting_precinct_count":len(ids),"source_voting_precinct_ids":ids,
               "assignment_confidence_min":round(min(cs),6),"assignment_confidence_mean":round(statistics.fmean(cs),6),
               "official_map_sha256":msha,"tlc_precinct_zip_sha256":zsha}
        geom=rounded(mapping(g));raw.append({"type":"Feature","properties":attrs,"geometry":geom})
        canonical.append({"type":"Feature","properties":{"geometry_id":f"kaufman-county-commissioner-precinct-{d}",
          "record_id":f"TX:county:kaufman:commissioner_precinct:{d}","jurisdiction_name":"Kaufman County",
          "district_type":"commissioner_precinct","district_id":d,"district_name":f"Commissioner Precinct {d}",
          "source_agency":"Kaufman County and Texas Legislative Council","source_layer":a.precinct_url,
          "source_request_url":a.precinct_url,"source_retrieved_at":a.retrieved_at,
          "source_district_field":"official_map_color_assignment","source_attributes":attrs},"geometry":geom});summary[d]=attrs
    diff=union4326.symmetric_difference(repair(unary_union(dissolved))).area
    overlap=sum(first.intersection(second).area for i,first in enumerate(dissolved) for second in dissolved[i+1:])
    if diff>1e-12 or overlap>1e-12:raise ValueError({"difference":diff,"overlap":overlap})
    dump(a.raw_output,{"type":"FeatureCollection","features":raw});dump(a.output,{"type":"FeatureCollection","features":canonical})
    cs=[x["confidence"] for x in assignments]
    contract={"derivation_type":"authoritative_composite",
      "official_gis_application_url":"https://gis.kaufmancounty.net/portal/apps/webappviewer/index.html?id=da2d7bb2339b4c67bfe382fc24bb775a",
      "official_gis_host_status":{"hostname":"gis.kaufmancounty.net","resolved_ipv4":"67.133.180.13","observed_failure":"TCP/HTTPS connection timeout from GitHub-hosted runners"},
      "official_commissioner_map_url":a.official_map_url,"official_commissioner_map_sha256":msha,
      "official_commissioner_map_dimensions":list(MAP_SIZE),"map_pixel_bbox":list(MAP_BBOX),
      "map_anchor_rgb":{k:list(v) for k,v in COLORS.items()},"map_anchor_pixels":{k:list(v) for k,v in ANCHORS.items()},
      "tlc_precinct_resource_url":a.precinct_url,"tlc_precinct_zip_sha256":zsha,"tlc_precinct_metadata":meta,
      "assignment_method":"Web-Mercator county-bounds georeference of the pinned official PNG; multi-point nearest-color classification of each 2026 TLC voting precinct; dissolve by majority assignment.",
      "assignment_confidence_min":round(min(cs),6),"assignment_confidence_mean":round(statistics.fmean(cs),6),
      "all_voting_precincts_assigned":len(assignments)==meta["voting_precinct_count"],
      "commissioner_precinct_ids":["1","2","3","4"],"commissioner_summary":summary,
      "union_symmetric_difference_area_degrees":diff,"interdistrict_overlap_area_degrees":overlap,
      "source_hierarchy":["Kaufman County official Commissioner map controls district assignment.",
       "Texas Legislative Council 2026 primary voting precincts control polygon geometry.",
       "Kaufman County's 2021 final redistricting action requires voting precincts to conform to Commissioner precinct boundaries."],
      "source_retrieved_at":a.retrieved_at}
    dump(a.contract_output,contract);dump(a.evidence_output,{"contract":contract,"assignments":assignments,"county_bounds_epsg3857":list(union3857.bounds)})
    print(f"Derived 4 Commissioner precincts from {len(assignments)} voting precincts; min confidence {min(cs):.3f}.")
    return 0
if __name__=="__main__":raise SystemExit(main())
