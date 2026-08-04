#!/usr/bin/env python3
"""Verify Presidio County ballot-to-Commissioner mapping and current TLC polygons."""
from __future__ import annotations
import hashlib, json, re, shutil, time, urllib.request, zipfile
from pathlib import Path
import fitz, shapefile

BASE="https://www.co.presidio.tx.us/upload/page/4732"
BALLOTS={
 "1":f"{BASE}/2024/november_2024_general_election_sample_ballotskj.pdf",
 "3":f"{BASE}/2026/Precinct%203%20Sample%20Ballot%20Dem%20Primary.pdf",
 "4":f"{BASE}/2026/Precinct%204%20Sample%20Ballot%20Dem%20Primary.pdf",
 "7":f"{BASE}/2026/Precinct%207%20Sample%20Ballot%20Dem%20Primary.pdf",
}
TLC_URL="https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip"
UA="Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
EXPECTED={"1":"1","2":"1","3":"2","4":"2","5":"3","6":"3","7":"4"}

def download(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(1,6):
  try:
   req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity"})
   with urllib.request.urlopen(req,timeout=180) as src,path.open("wb") as dst: shutil.copyfileobj(src,dst,1<<20)
   if path.stat().st_size:return
  except Exception:
   path.unlink(missing_ok=True)
   if attempt==5:raise
   time.sleep(attempt*3)

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()

def text(path):
 doc=fitz.open(path);return "\n".join(page.get_text() for page in doc)

def norm(v):
 s=str(v or "").strip()
 if s.endswith('.0'):s=s[:-2]
 return s.lstrip('0') or '0'

def main():
 out=Path('build/presidio-bootstrap');work=out/'work';out.mkdir(parents=True,exist_ok=True);work.mkdir(parents=True,exist_ok=True)
 proofs={}
 general=out/'2024-general-ballots.pdf';download(BALLOTS['1'],general);gt=text(general)
 for precinct,commissioner in {'1':'1','2':'1','5':'3','6':'3'}.items():
  block=re.search(rf"Precinct\s+{precinct}\b(.*?)(?=Precinct\s+{int(precinct)+1}\b|\Z)",gt,re.S|re.I)
  if not block or not re.search(rf"County Commissioner,\s*Precinct No[.,]?\s*{commissioner}\b",block.group(1),re.I):
   raise SystemExit(f'2024 ballot did not prove precinct {precinct} -> commissioner {commissioner}')
  proofs[precinct]={"commissioner_precinct":commissioner,"source":"2024 general ballot"}
 for precinct in ('3','4','7'):
  pdf=out/f'2026-primary-precinct-{precinct}.pdf';download(BALLOTS[precinct],pdf);body=text(pdf)
  match=re.search(r"County Commissioner,\s*Precinct No[.,]?\s*(\d)",body,re.I)
  if not match:raise SystemExit(f'No commissioner race found in precinct {precinct} ballot')
  commissioner=match.group(1)
  if commissioner!=EXPECTED[precinct]:raise SystemExit(f'Precinct {precinct} mapped to {commissioner}, expected {EXPECTED[precinct]}')
  proofs[precinct]={"commissioner_precinct":commissioner,"source":"2026 Democratic primary ballot","sha256":sha(pdf)}
 z=work/'precincts26p.zip';download(TLC_URL,z);extract=work/'precincts';shutil.rmtree(extract,ignore_errors=True);extract.mkdir()
 with zipfile.ZipFile(z) as a:a.extractall(extract)
 shp=next(extract.rglob('*.shp'));reader=shapefile.Reader(str(shp));fields=[f[0] for f in reader.fields[1:]];lookup={f.casefold():f for f in fields}
 fips=next((lookup[n] for n in ('fips','cnty','countyfp','county_fip') if n in lookup),None);county=next((lookup[n] for n in ('county','countyname','cntyname','name') if n in lookup),None);prec=next((lookup[n] for n in ('prec','precinct','pct','pctkey','vtd','cntyvtd') if n in lookup),None)
 if not prec or not(fips or county):raise SystemExit(fields)
 ids=[]
 for sr in reader.iterShapeRecords():
  row=dict(zip(fields,sr.record));match=bool(fips and norm(row.get(fips))=='377') or bool(county and str(row.get(county) or '').strip().casefold()=='presidio')
  if match:ids.append(norm(row.get(prec)))
 ids=sorted(set(ids),key=int)
 if ids!=list(EXPECTED):raise SystemExit(f'TLC precinct IDs {ids} != {list(EXPECTED)}')
 report={"ballot_assignments":proofs,"expected_assignments":EXPECTED,"general_ballot_sha256":sha(general),"tlc_zip_sha256":sha(z),"tlc_precinct_ids":ids,"tlc_precinct_count":len(ids),"tlc_url":TLC_URL}
 (out/'discovery.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps(report,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
