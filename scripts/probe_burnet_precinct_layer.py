#!/usr/bin/env python3
from __future__ import annotations
import json,urllib.parse,urllib.request
from pathlib import Path
URL="https://services3.arcgis.com/et3BBCaOmTkrlfxA/arcgis/rest/services/Online_Map_Final_WFL1/FeatureServer/3"
HEAD={"User-Agent":"Civic-Cartography/0.1","Accept-Encoding":"identity"}
def get(url):
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode("utf-8",errors="replace"))
def main():
    out=Path("build/burnet-layer-probe");out.mkdir(parents=True,exist_ok=True)
    meta=get(URL+"?f=json")
    q=URL+"/query?"+urllib.parse.urlencode({"where":"1=1","outFields":"*","returnGeometry":"false","resultRecordCount":2000,"f":"json"})
    payload=get(q);attrs=[f.get("attributes",{}) for f in payload.get("features",[])]
    unique={}
    for f in meta.get("fields",[]):
        name=f.get("name");vals=sorted({str(a.get(name)) for a in attrs if a.get(name) is not None})
        unique[name]=vals[:200]
    report={"url":URL,"meta":meta,"feature_count":len(attrs),"attributes":attrs,"unique_values":unique}
    (out/"layer.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"feature_count":len(attrs),"fields":unique},indent=2))
if __name__=="__main__":main()
