#!/usr/bin/env python3
"""Resolve Burnet County's official ArcGIS graph to precinct source polygons."""
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
            if attempt<4:time.sleep(attempt*3)
    raise RuntimeError(f"GET failed {url}: {last}")

def item_url(item_id:str,data:bool=False)->str:
    return f"https://www.arcgis.com/sharing/rest/content/items/{item_id}{'/data' if data else ''}?f=json"

def search(query:str)->list[dict]:
    url="https://www.arcgis.com/sharing/rest/search?"+urllib.parse.urlencode({"f":"json","num":100,"q":query})
    return get(url).get("results",[])

def clean(value)->str:
    text=str(value or "").strip()
    return text[:-2] if text.endswith(".0") else text

def main()->int:
    out=Path("build/burnet-county-bootstrap");out.mkdir(parents=True,exist_ok=True)
    app_meta=get(item_url(APP));owner=app_meta.get("owner");orgid=app_meta.get("orgId")
    searches=["Burnet County precinct commissioner",'"Burnet County" precinct',"Burnet commissioner precinct"]
    if owner:searches.extend([f"owner:{owner} precinct",f"owner:{owner} Burnet"])
    if orgid:searches.extend([f"orgid:{orgid} precinct",f"orgid:{orgid} Burnet"])
    search_results=[];item_ids=[APP]
    for query in searches:
        try:rows=search(query)
        except Exception as exc:search_results.append({"query":query,"error":str(exc)});continue
        search_results.append({"query":query,"results":rows})
        for row in rows:
            item_id=str(row.get("id") or "").lower()
            if len(item_id)==32 and item_id not in item_ids:item_ids.append(item_id)
    seen=set();items={};services=set()
    id_re=re.compile(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])",re.I)
    url_re=re.compile(r"https?://[^\"'<>\\s]+(?:FeatureServer|MapServer)(?:/\d+)?",re.I)
    while item_ids and len(seen)<160:
        item_id=item_ids.pop(0)
        if item_id in seen:continue
        seen.add(item_id)
        try:meta=get(item_url(item_id));data=get(item_url(item_id,True))
        except Exception as exc:items[item_id]={"error":str(exc)};continue
        items[item_id]={"meta":meta,"data":data}
        if meta.get("url") and re.search(r"(?:FeatureServer|MapServer)(?:/\d+)?$",str(meta["url"]),re.I):services.add(str(meta["url"]).rstrip("/"))
        text=json.dumps({"meta":meta,"data":data})
        for ref in id_re.findall(text):
            ref=ref.lower()
            if ref not in seen and ref not in item_ids:item_ids.append(ref)
        services.update(url.rstrip("/") for url in url_re.findall(text))
    candidates=[];inspected=[]
    def inspect(layer_url:str,origin:str)->None:
        try:meta=get(layer_url+"?f=json")
        except Exception as exc:inspected.append({"url":layer_url,"origin":origin,"error":str(exc)});return
        record={"url":layer_url,"origin":origin,"name":meta.get("name"),"geometryType":meta.get("geometryType")};inspected.append(record)
        if meta.get("geometryType")!="esriGeometryPolygon":return
        query=layer_url+"/query?"+urllib.parse.urlencode({"where":"1=1","outFields":"*","returnGeometry":"false","resultRecordCount":2000,"f":"json"})
        try:rows=get(query).get("features",[])
        except Exception as exc:record["query_error"]=str(exc);return
        attrs=[row.get("attributes",{}) for row in rows];fields=[]
        for field in meta.get("fields",[]):
            name=field.get("name");values=sorted({clean(row.get(name)) for row in attrs if row.get(name) is not None})
            if values==["1","2","3","4"]:fields.append(name)
        if not fields:return
        text=(str(meta.get("name",""))+" "+layer_url+" "+origin).casefold();score=0
        if "commission" in text:score+=12
        if "precinct" in text:score+=8
        if "burnet" in text:score+=6
        if "county" in text:score+=2
        if len(rows)==4:score+=6
        candidates.append({"url":layer_url,"origin":origin,"name":meta.get("name"),"fields":fields,"score":score,"feature_count":len(rows),"attributes":attrs[:50]})
    for service in sorted(services):
        if service.rstrip("/").split("/")[-1].isdigit():inspect(service,"item_graph_or_search");continue
        try:meta=get(service+"?f=json")
        except Exception as exc:inspected.append({"url":service,"origin":"service_root","error":str(exc)});continue
        layers=meta.get("layers") or []
        if layers:
            for layer in layers:inspect(service+"/"+str(layer["id"]),"service_sublayer")
        elif meta.get("geometryType"):inspect(service,"service_root")
    candidates.sort(key=lambda row:(row["score"],-row["feature_count"],row["name"] or ""),reverse=True)
    winner=candidates[0] if candidates else None
    geojson_url=None
    if winner:
        geojson_url=winner["url"]+"/query?"+urllib.parse.urlencode({"where":"1=1","outFields":"*","returnGeometry":"true","outSR":"4326","f":"geojson"})
        req=urllib.request.Request(geojson_url,headers=HEAD)
        with urllib.request.urlopen(req,timeout=120) as r:geojson=json.loads(r.read().decode("utf-8"))
        (out/"precinct-source.geojson").write_text(json.dumps(geojson,sort_keys=True,separators=(",",":"))+"\n")
    report={"application_item_id":APP,"application_owner":owner,"application_org_id":orgid,"searches":search_results,"items":items,"service_urls":sorted(services),"inspected":inspected,"candidates":candidates,"winner":winner,"winner_geojson_url":geojson_url}
    (out/"discovery.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"winner":winner,"item_count":len(items),"service_count":len(services),"candidate_count":len(candidates)},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
