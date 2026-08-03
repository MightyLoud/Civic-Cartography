#!/usr/bin/env python3
"""Fetch the four-county 33rd/424th District Attorney service area."""
from __future__ import annotations
import argparse, json, urllib.parse, urllib.request
from pathlib import Path
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

LAYER="https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/82"
GEOIDS={"48031":"Blanco County","48053":"Burnet County","48299":"Llano County","48411":"San Saba County"}
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
def fetch(geoid:str):
    params={"where":f"GEOID='{geoid}'","outFields":"*","returnGeometry":"true","outSR":"4326","f":"geojson"}
    url=f"{LAYER}/query?{urllib.parse.urlencode(params)}";req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
    with urllib.request.urlopen(req,timeout=90) as response:payload=json.load(response)
    features=payload.get("features") or []
    if len(features)!=1:raise ValueError(f"{geoid}: expected one feature, found {len(features)}")
    return features[0],url
def rounded(value):
    if isinstance(value,float):return round(value,7)
    if isinstance(value,list):return [rounded(v) for v in value]
    if isinstance(value,dict):return {k:rounded(v) for k,v in value.items()}
    return value
def dump(path:Path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--retrieved-at",required=True)
    p.add_argument("--raw-output",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--contract-output",type=Path,required=True);a=p.parse_args()
    raw=[];geometries=[];requests={}
    for geoid,name in GEOIDS.items():
        feature,url=fetch(geoid);requests[geoid]=url;props=dict(feature.get("properties") or {});props["component_county_name"]=name;props["component_county_geoid"]=geoid
        raw.append({"type":"Feature","properties":props,"geometry":rounded(feature["geometry"])});geometries.append(shape(feature["geometry"]))
    union=unary_union(geometries)
    if union.is_empty or union.geom_type not in {"Polygon","MultiPolygon"}:raise ValueError(union.geom_type)
    component_geoids=list(GEOIDS);component_names=[GEOIDS[g] for g in component_geoids]
    properties={"geometry_id":"burnet-33rd-424th-district-attorney-service-area","record_id":"TX:judicial_district:33-424:district_attorney_service_area:33-424",
      "jurisdiction_name":"33rd & 424th Judicial Districts","district_type":"district_attorney_service_area","district_id":"33-424",
      "district_name":"District Attorney Service Area — 33rd & 424th Judicial Districts","source_agency":"U.S. Census Bureau","source_layer":LAYER,
      "source_request_urls":requests,"source_retrieved_at":a.retrieved_at,"component_counties":component_names,"component_county_geoids":component_geoids,"component_count":4}
    contract={"derivation_type":"exact_union_of_current_census_counties","component_counties":component_names,"component_county_geoids":component_geoids,
      "component_count":4,"includes_burnet_county":True,"district_attorney_service_area_is_burnet_only":False,"source_layer":LAYER,
      "source_request_urls":requests,"source_retrieved_at":a.retrieved_at}
    dump(a.raw_output,{"type":"FeatureCollection","features":raw});dump(a.output,{"type":"FeatureCollection","features":[{"type":"Feature","properties":properties,"geometry":rounded(mapping(union))}]});dump(a.contract_output,contract)
    print("Built the four-county 33rd/424th District Attorney service area.");return 0
if __name__=="__main__":raise SystemExit(main())
