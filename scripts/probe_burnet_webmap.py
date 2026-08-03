#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.request
from pathlib import Path
PORTAL="https://buco911.maps.arcgis.com"
ITEM="db6773e2429d46a39f7ed9250faa01dd"
HEAD={"User-Agent":"Civic-Cartography/0.1","Accept-Encoding":"identity"}
def get(url):
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode("utf-8",errors="replace"))
def main():
    out=Path('build/burnet-webmap');out.mkdir(parents=True,exist_ok=True)
    meta=get(f'{PORTAL}/sharing/rest/content/items/{ITEM}?f=json')
    data=get(f'{PORTAL}/sharing/rest/content/items/{ITEM}/data?f=json')
    text=json.dumps(data)
    urls=sorted(set(re.findall(r'https?://[^\"\'<>\\s]+(?:FeatureServer|MapServer)(?:/\d+)?',text,re.I)))
    payload={'portal':PORTAL,'item_id':ITEM,'meta':meta,'data':data,'service_urls':urls}
    (out/'webmap.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'title':meta.get('title'),'owner':meta.get('owner'),'urls':urls},indent=2))
if __name__=='__main__':main()
