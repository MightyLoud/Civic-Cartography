#!/usr/bin/env python3
from __future__ import annotations
import json,re,urllib.parse,urllib.request
from pathlib import Path
APP="54aa0faa57064472a3cb2039b0e115ad"
HEAD={"User-Agent":"Civic-Cartography/0.1","Accept-Encoding":"identity"}
def get(url):
    req=urllib.request.Request(url,headers=HEAD)
    with urllib.request.urlopen(req,timeout=45) as r:return json.loads(r.read().decode("utf-8",errors="replace"))
def item(i,data=False):return get(f"https://www.arcgis.com/sharing/rest/content/items/{i}{'/data' if data else ''}?f=json")
def search(q):return get("https://www.arcgis.com/sharing/rest/search?"+urllib.parse.urlencode({"f":"json","num":100,"q":q})).get("results",[])
def main():
    out=Path("build/burnet-arcgis-index");out.mkdir(parents=True,exist_ok=True)
    meta=item(APP);data=item(APP,True);text=json.dumps(data);ids=sorted(set(re.findall(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])",text,re.I)))
    queries=['"Burnet County" precinct','Burnet commissioner precinct','Burnet voting precinct']
    if meta.get('owner'):queries += [f"owner:{meta['owner']} precinct",f"owner:{meta['owner']} commissioner",f"owner:{meta['owner']} Burnet"]
    if meta.get('orgId'):queries += [f"orgid:{meta['orgId']} precinct",f"orgid:{meta['orgId']} commissioner"]
    results=[]
    for q in queries:
        try:rows=search(q)
        except Exception as e:results.append({'query':q,'error':str(e)});continue
        results.append({'query':q,'results':[{k:r.get(k) for k in ('id','title','type','owner','url','modified','description','tags')} for r in rows]})
    embedded=[]
    for i in ids[:30]:
        try:m=item(i);d=item(i,True);embedded.append({'id':i,'meta':m,'data':d})
        except Exception as e:embedded.append({'id':i,'error':str(e)})
    payload={'app_meta':meta,'app_data':data,'embedded_item_ids':ids,'embedded_items':embedded,'searches':results}
    (out/'index.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'owner':meta.get('owner'),'orgId':meta.get('orgId'),'embedded_ids':ids,'search_result_counts':[(r['query'],len(r.get('results',[]))) for r in results]},indent=2))
if __name__=='__main__':main()
