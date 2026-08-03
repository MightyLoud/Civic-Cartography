#!/usr/bin/env python3
"""Resolve Burnet County's official ArcGIS application to Commissioner polygons."""
from __future__ import annotations
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

APP="54aa0faa57064472a3cb2039b0e115ad"
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
HEAD={"User-Agent":UA,"Accept-Encoding":"identity"}

def get(url:str):
    last=None
    for attempt in range(1,5):
        try:
            req=urllib.request.Request(url,headers=HEAD)
            with urllib.request.urlopen(req,timeout=90) as r:
                return json.loads(r.read().decode("utf-8",errors="replace"))
        except Exception as exc:
            last=exc
            if attempt<4: time.sleep(attempt*3)
    raise RuntimeError(f"GET failed {url}: {last}")

def item_url(item_id:str,data:bool=False)->str:
    return f"https://www.arcgis.com/sharing/rest/content/items/{item_id}{'/data' if data else ''}?f=json"

def main()->int:
    out=Path("build/burnet-county-bootstrap");out.mkdir(parents=True,exist_ok=True)
    item_ids=[APP];seen=set();items={};services=set()
    id_re=re.compile(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])",re.I)
    url_re=re.compile(r"https?://[^\"'<>\\s]+(?:FeatureServer|MapServer)(?:/\d+)?",re.I)
    while item_ids and len(seen)<40:
        item_id=item_ids.pop(0)
        if item_id in seen:continue
        seen.add(item_id);meta=get(item_url(item_id));data=get(item_url(item_id,True));items[item_id]={"meta":meta,"data":data}
        text=json.dumps({"meta":meta,"data":data})
        for ref in id_re.findall(text):
            ref=ref.lower()
            if ref not in seen and ref not in item_ids:item_ids.append(ref)
        services.update(url.rstrip("/") for url in url_re.findall(text))
    candidates=[];inspected=[]
    def inspect(layer_url:str,origin:str)->None:
        try:meta=get(layer_url+"?f=json")
        except Exception as exc:inspected.append({"url":layer_url,"origin":origin,"error":str(exc)});return
        record={"url":layer_url,"origin":origin,"name":meta.get("name"),"type":meta.get("type"),"geometryType":meta.get("geometryType")};inspected.append(record)
        if meta.get("geometryType")!="esriGeometryPolygon":return
        query=layer_url+"/query?"+urllib.parse.urlencode({"where":"1=1","outFields":"*","returnGeometry":"false","f":"json"})
        try:rows=get(query).get("features",[])
        except Exception as exc:record["query_error"]=str(exc);return
        if len(rows)!=4:return
        attrs=[row.get("attributes",{}) for row in rows];fields=[]
        for field in meta.get("fields",[]):
            name=field.get("name");values=[]
            for row in attrs:
                value=row.get(name)
                if value is None:continue
                text=str(value).strip();values.append(text[:-2] if text.endswith(".0") else text)
            if sorted(set(values))==["1","2","3","4"]:fields.append(name)
        if not fields:return
        text=(str(meta.get("name",""))+" "+layer_url+" "+origin).casefold();score=0
        if "commission" in text:score+=8
        if "precinct" in text:score+=6
        if "burnet" in text:score+=4
        if "county" in text:score+=2
        candidates.append({"url":layer_url,"origin":origin,"name":meta.get("name"),"fields":fields,"score":score,"attributes":attrs})
    for service in sorted(services):
        if service.rstrip("/").split("/")[-1].isdigit():inspect(service,"embedded_url");continue
        try:meta=get(service+"?f=json")
        except Exception as exc:inspected.append({"url":service,"origin":"embedded_service","error":str(exc)});continue
        layers=meta.get("layers") or []
        if layers:
            for layer in layers:inspect(service+"/"+str(layer["id"]),"embedded_service")
        elif meta.get("geometryType"):inspect(service,"embedded_service")
    candidates.sort(key=lambda row:(row["score"],row["name"] or ""),reverse=True)
    if not candidates:raise SystemExit("No official four-polygon Commissioner candidate with stable values 1-4")
    winner=candidates[0]
    geojson_url=winner["url"]+"/query?"+urllib.parse.urlencode({"where":"1=1","outFields":"*","returnGeometry":"true","outSR":"4326","f":"geojson"})
    req=urllib.request.Request(geojson_url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=120) as r:geojson=json.loads(r.read().decode("utf-8"))
    if len(geojson.get("features",[]))!=4:raise SystemExit("Winner GeoJSON did not contain four features")
    (out/"commissioner-precincts.geojson").write_text(json.dumps(geojson,sort_keys=True,separators=(",",":"))+"\n")
    report={"application_item_id":APP,"items":items,"service_urls":sorted(services),"inspected":inspected,"candidates":candidates,"winner":winner,"winner_geojson_url":geojson_url}
    (out/"discovery.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"winner":winner,"feature_count":len(geojson["features"])},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
