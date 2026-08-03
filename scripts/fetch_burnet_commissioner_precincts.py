#!/usr/bin/env python3
"""Fetch Burnet County Commissioner precincts from the county-linked ArcGIS layer."""
from __future__ import annotations
import argparse, json, re, urllib.parse, urllib.request
from pathlib import Path

APP_ITEM="54aa0faa57064472a3cb2039b0e115ad"
LAYER="https://services3.arcgis.com/et3BBCaOmTkrlfxA/arcgis/rest/services/Online_Map_Final_WFL1/FeatureServer/3"
FIELD="NAME"
WHERE="NAME IS NOT NULL"
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"

def fetch_json(url:str):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
    with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
def dump(path:Path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
def rounded(value):
    if isinstance(value,float):return round(value,7)
    if isinstance(value,list):return [rounded(v) for v in value]
    if isinstance(value,dict):return {k:rounded(v) for k,v in value.items()}
    return value
def district(value)->str:
    match=re.fullmatch(r"\s*Pct\.\s*([1-4])\s*",str(value or ""))
    if not match:raise ValueError(f"Unrecognized Commissioner precinct label: {value!r}")
    return match.group(1)

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--retrieved-at",required=True)
    p.add_argument("--raw-output",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--contract-output",type=Path,required=True);a=p.parse_args()
    meta=fetch_json(LAYER+"?f=json")
    all_count=fetch_json(LAYER+"/query?"+urllib.parse.urlencode({"where":"1=1","returnCountOnly":"true","f":"json"}))["count"]
    params={"where":WHERE,"outFields":"*","returnGeometry":"true","outSR":"4326","f":"geojson"}
    query=LAYER+"/query?"+urllib.parse.urlencode(params)
    payload=fetch_json(query);source=payload.get("features") or []
    if len(source)!=4:raise ValueError(f"Expected four filtered Commissioner features, found {len(source)}")
    rows=[]
    for feature in source:
        props=dict(feature.get("properties") or {});d=district(props.get(FIELD))
        rows.append((d,{"type":"Feature","properties":props,"geometry":rounded(feature["geometry"])}))
    rows.sort(key=lambda row:row[0])
    if [d for d,_ in rows]!=["1","2","3","4"]:raise ValueError([d for d,_ in rows])
    raw={"type":"FeatureCollection","features":[feature for _,feature in rows]}
    canonical=[]
    for d,feature in rows:
        attrs=dict(feature["properties"])
        canonical.append({"type":"Feature","properties":{
          "geometry_id":f"burnet-county-commissioner-precinct-{d}",
          "record_id":f"TX:county:burnet:commissioner_precinct:{d}",
          "jurisdiction_name":"Burnet County",
          "district_type":"commissioner_precinct",
          "district_id":d,
          "district_name":f"Commissioner Precinct {d}",
          "source_agency":"Burnet County 9-1-1 Addressing",
          "source_application_item_id":APP_ITEM,
          "source_layer":LAYER,
          "source_request_url":query,
          "source_retrieved_at":a.retrieved_at,
          "source_district_field":FIELD,
          "source_attributes":attrs,
        },"geometry":feature["geometry"]})
    contract={
      "application_item_id":APP_ITEM,
      "source_layer_url":LAYER,
      "source_layer_name":meta.get("name"),
      "source_layer_last_edit_date":(meta.get("editingInfo") or {}).get("lastEditDate"),
      "district_field":FIELD,
      "district_label_pattern":"Pct. <1-4>",
      "source_filter":WHERE,
      "total_layer_feature_count":all_count,
      "source_feature_count":len(source),
      "excluded_null_feature_count":all_count-len(source),
      "commissioner_feature_count":4,
      "commissioner_precinct_ids":["1","2","3","4"],
      "source_request_url":query,
      "source_retrieved_at":a.retrieved_at,
      "null_artifact_policy":"Features with blank NAME are maintenance artifacts and are excluded before publication.",
    }
    dump(a.raw_output,raw);dump(a.output,{"type":"FeatureCollection","features":canonical});dump(a.contract_output,contract)
    print(f"Fetched four Burnet County Commissioner precincts; excluded {all_count-len(source)} null artifact(s).")
    return 0
if __name__=="__main__":raise SystemExit(main())
