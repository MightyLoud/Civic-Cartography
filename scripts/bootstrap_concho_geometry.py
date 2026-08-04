#!/usr/bin/env python3
"""Inspect Concho County's official Commissioner map and current TLC precincts."""
from __future__ import annotations
import hashlib, json, shutil, time, urllib.request, zipfile
from pathlib import Path
import fitz, shapefile

MAP_URL="https://www.co.concho.tx.us/upload/page/6097/County%20Precinct%20Map_11222023102640.PDF"
TLC_URL="https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip"
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
COUNTY_FIPS="95"
COUNTY_NAME="concho"

def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1,6):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
            with urllib.request.urlopen(req,timeout=180) as src,path.open("wb") as dst: shutil.copyfileobj(src,dst,1<<20)
            if path.stat().st_size:return
        except Exception:
            path.unlink(missing_ok=True)
            if attempt==5:raise
            time.sleep(attempt*4)

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def code(value):
    text=str(value or "").strip()
    if text.endswith(".0"):text=text[:-2]
    return text.lstrip("0") or "0"

def main()->int:
    out=Path("build/concho-bootstrap");work=out/"work";out.mkdir(parents=True,exist_ok=True);work.mkdir(parents=True,exist_ok=True)
    pdf=out/"official-commissioner-map.pdf";z=work/"precincts26p.zip"
    download(MAP_URL,pdf);download(TLC_URL,z)
    doc=fitz.open(pdf)
    if len(doc)!=1:raise SystemExit(f"Expected one page, found {len(doc)}")
    page=doc[0];zoom=1800/page.rect.width;pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False);pix.save(out/"official-commissioner-map.png")
    extract=work/"precincts";shutil.rmtree(extract,ignore_errors=True);extract.mkdir(parents=True)
    with zipfile.ZipFile(z) as archive:archive.extractall(extract)
    shp=list(extract.rglob("*.shp"))[0];reader=shapefile.Reader(str(shp));fields=[f[0] for f in reader.fields[1:]]
    lookup={f.casefold():f for f in fields};fips=next((lookup[n] for n in ("fips","cnty","countyfp","county_fip") if n in lookup),None);county=next((lookup[n] for n in ("county","countyname","cntyname","name") if n in lookup),None);prec=next((lookup[n] for n in ("prec","precinct","pct","pctkey","vtd","cntyvtd") if n in lookup),None)
    if not prec or not (fips or county):raise SystemExit(fields)
    records=[]
    for sr in reader.iterShapeRecords():
        row=dict(zip(fields,sr.record));match=bool(fips and code(row.get(fips))==COUNTY_FIPS) or bool(county and str(row.get(county) or "").strip().casefold()==COUNTY_NAME)
        if match:records.append(row)
    ids=sorted({code(r.get(prec)) for r in records},key=int)
    expected=["101","102","203","204","205","306","407","408"]
    if ids!=expected:raise SystemExit(f"Unexpected Concho precinct IDs: {ids}")
    report={"official_map_url":MAP_URL,"official_map_sha256":sha(pdf),"official_map_bytes":pdf.stat().st_size,"official_map_page_count":len(doc),"official_map_render_size":[pix.width,pix.height],"tlc_url":TLC_URL,"tlc_zip_sha256":sha(z),"tlc_zip_bytes":z.stat().st_size,"fields":fields,"fips_field":fips,"county_field":county,"precinct_field":prec,"voting_precinct_count":len(records),"normalized_precinct_ids":ids,"commissioner_assignments":{i:i[0] for i in ids},"records":records}
    (out/"discovery.json").write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+"\n")
    print(json.dumps({k:report[k] for k in ("official_map_sha256","official_map_page_count","official_map_render_size","tlc_zip_sha256","voting_precinct_count","normalized_precinct_ids","commissioner_assignments")},indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
