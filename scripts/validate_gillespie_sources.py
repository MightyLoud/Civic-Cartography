#!/usr/bin/env python3
"""Validate Gillespie County roster, County Surveyor, scope, and sources."""
from __future__ import annotations
import csv, html, json, re, time, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/gillespie-county/current-elected-offices.csv"
SURVEYOR=ROOT/"data/raw/gillespie-county/county-surveyor-office.csv"
NON_SCOPE=ROOT/"data/raw/gillespie-county/non-scope-offices.csv"
MANIFEST=ROOT/"data/raw/gillespie-county/source-manifest.csv"
CONTRACT=ROOT/"data/raw/gillespie-county/gis-source-contract.json"
EXPECTED={
"County Judge":"Daniel Jones","County Commissioner Precinct 1":"Charles Olfers",
"County Commissioner Precinct 2":"Keith Kramer","County Commissioner Precinct 3":"Charles “Chuck” Jenschke",
"County Commissioner Precinct 4":"Don Weinheimer","Sheriff":"Christopher “Chris” Ayala",
"County Clerk":"Lindsey Brown","District Clerk":"McKenna Monk Herbort",
"Tax Assessor-Collector":"Carol Rode Durst","County Treasurer":"Vicki J. Schmidt",
"County Surveyor":"Don Kuhlmann, RPLS"}
HEADERS={"User-Agent":"Mozilla/5.0 Civic-Cartography-validator/1.0","Accept-Encoding":"identity"}
def searchable(v:str)->str:return re.sub(r"[^a-z0-9]+"," ",v.casefold()).strip()
def fetch(url:str)->str|None:
    for attempt in range(1,4):
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=45) as response:return html.unescape(response.read().decode("utf-8",errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in {403,404,429}:return None
        except Exception:pass
        if attempt<3:time.sleep(attempt*3)
    return None
def require(page:str|None,url:str,markers:tuple[str,...])->None:
    if page is None:return
    text=searchable(page);missing=[m for m in markers if searchable(m) not in text]
    if missing:raise SystemExit(f"{url} lost markers: {missing}")
def committed()->None:
    with ROSTER.open(newline="",encoding="utf-8") as h:rows=list(csv.DictReader(h))
    actual={r["office_name"]:r["officeholder"] for r in rows}
    if len(rows)!=11 or actual!=EXPECTED:raise SystemExit(f"Gillespie roster changed: {actual!r}")
    if len(set(actual.values()))!=11 or {r["selection_method"] for r in rows}!={"election"}:raise SystemExit("Gillespie selection or uniqueness changed")
    if sum(r["office_name"]=="County Surveyor" for r in rows)!=1:raise SystemExit("Expected one County Surveyor")
    if any(r["office_name"]=="County Engineer" for r in rows):raise SystemExit("County Engineer leaked into elected roster")
    with SURVEYOR.open(newline="",encoding="utf-8") as h:s=list(csv.DictReader(h))
    if len(s)!=1:raise SystemExit("Expected one County Surveyor structure row")
    row=s[0]
    if row["current_officeholder"]!="Don Kuhlmann, RPLS" or row["office_status"]!="active_elected_office" or row["term_length_years"]!="4":raise SystemExit(f"Surveyor contract changed: {row!r}")
    if row["separate_county_engineer"]!="TRUE" or "future-election evidence only" not in row["future_candidate_evidence"]:raise SystemExit("Surveyor/engineer or candidate contract changed")
    with NON_SCOPE.open(newline="",encoding="utf-8") as h:non=list(csv.DictReader(h))
    engineer=next((r for r in non if r["office_name"]=="County Engineer"),None)
    if not engineer or "Melissa Eckert" not in engineer["current_officeholder"]:raise SystemExit("County Engineer non-scope evidence missing")
    with MANIFEST.open(newline="",encoding="utf-8") as h:sources=list(csv.DictReader(h))
    if len(sources)!=19:raise SystemExit(f"Expected 19 sources, found {len(sources)}")
    ids={r["source_id"] for r in sources}
    required={"gillespie-county-surveyor","gillespie-engineering","gillespie-candidate-filings","texas-constitution-16-44","texas-natural-resources-code-23-011","gillespie-official-commissioner-map","texas-legislative-council-voting-precincts","census-gillespie-county"}
    if not required.issubset(ids):raise SystemExit(f"Manifest missing: {required-ids}")
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected={"derivation_type":"authoritative_composite","official_commissioner_map_sha256":"5409b6592515efe37af4bbff12a2923e782794f2bbc4d077035a8f0163f3fd70","tlc_precinct_zip_sha256":"70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107","all_voting_precincts_assigned":True,"commissioner_precinct_ids":["1","2","3","4"],"union_symmetric_difference_area_degrees":0.0,"interdistrict_overlap_area_degrees":0.0}
    for key,value in expected.items():
        if contract.get(key)!=value:raise SystemExit(f"Gillespie contract changed: {key}={contract.get(key)!r}")
    if contract["tlc_precinct_metadata"]["voting_precinct_count"]!=13 or contract["assignment_confidence_min"]<0.9:raise SystemExit("Gillespie assignment contract regressed")
    if sum(v["source_voting_precinct_count"] for v in contract["commissioner_summary"].values())!=13:raise SystemExit("Gillespie assignment count changed")
def live()->None:
    contracts=[
      ("https://www.gillespiecounty.gov/1292/Commissioners-Court",("Daniel Jones","Charles Olfers","Keith Kramer","Jenschke","Don Weinheimer")),
      ("https://www.gillespiecounty.gov/1205/County-Surveyor",("Don Kuhlmann","County Surveyor")),
      ("https://www.gillespiecounty.gov/1206/County-Sheriff",("Ayala",)),
      ("https://www.gillespiecounty.gov/1211/County-Clerk",("Lindsey Brown",)),
      ("https://www.gillespiecounty.gov/1200/District-Clerk",("McKenna","Herbort")),
      ("https://www.gillespiecounty.gov/1204/County-Tax-Assessor-Collector",("Carol","Durst")),
      ("https://www.gillespiecounty.gov/1203/County-Treasurer",("Vicki","Schmidt")),
      ("https://gillespiecounty.gov/1198/Engineering-Department",("Melissa Eckert","County Engineer")),
      ("https://www.gillespiecounty.gov/1318/Candidate-Campaign-Information",("Kuhlmann",)),
      ("https://www.gillespiecounty.gov/1261/Precinct-Maps",("Effective January 1, 2022","Commissioner Precinct Map")),]
    accessible=0
    for url,markers in contracts:
        page=fetch(url);accessible+=page is not None;require(page,url,markers)
    print(f"Validated {accessible} live Gillespie County page contract(s).")
def main()->None:committed();live();print("Gillespie County roster, County Surveyor, scope, and source contracts are valid.")
if __name__=="__main__":main()
