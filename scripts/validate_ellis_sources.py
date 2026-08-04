#!/usr/bin/env python3
"""Validate Ellis County roster, combined prosecutor, scope, and sources."""
from __future__ import annotations
import csv, html, json, re, time, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/ellis-county/current-elected-offices.csv"
COMBINED=ROOT/"data/raw/ellis-county/combined-prosecutor-structure.csv"
NON_SCOPE=ROOT/"data/raw/ellis-county/non-scope-offices.csv"
MANIFEST=ROOT/"data/raw/ellis-county/source-manifest.csv"
CONTRACT=ROOT/"data/raw/ellis-county/gis-source-contract.json"
EXPECTED={"County Judge":"John Wray","County Commissioner Precinct 1":"Randy Stinson","County Commissioner Precinct 2":"Lane Grayson","County Commissioner Precinct 3":"Louis Ponder","County Commissioner Precinct 4":"Kyle Butler","Sheriff":"Brad Norman","County and District Attorney":"Lindy Beaty","County Clerk":"Krystal Valdez","District Clerk":"Melanie Reed","Tax Assessor-Collector":"Richard Rozier","County Treasurer":"Cheryl Chambers"}
EXPECTED_GROUPS={"1":[*[str(v) for v in range(1001,1015)],"1060"],"2":[str(v) for v in range(1015,1027)],"3":[*[str(v) for v in range(1027,1040)],"1061"],"4":[str(v) for v in range(1040,1060)]}
HEADERS={"User-Agent":"Mozilla/5.0 Civic-Cartography-validator/1.0","Accept-Encoding":"identity"}
def rows(path):
    with path.open(newline="",encoding="utf-8") as h:return list(csv.DictReader(h))
def searchable(value):return re.sub(r"[^a-z0-9]+"," ",value.casefold()).strip()
def fetch(url):
    for attempt in range(1,4):
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=45) as r:return html.unescape(r.read().decode("utf-8",errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in {403,404,429,500,502,503,504}:return None
        except Exception:pass
        if attempt<3:time.sleep(attempt*3)
    return None
def require(page,url,markers):
    if page is None:return
    text=searchable(page);missing=[m for m in markers if searchable(m) not in text]
    if missing:raise SystemExit(f"{url} lost markers: {missing}")
def committed():
    roster=rows(ROSTER);actual={r["office_name"]:r["officeholder"] for r in roster}
    if len(roster)!=11 or actual!=EXPECTED:raise SystemExit(f"Ellis roster changed: {actual!r}")
    if len(set(actual.values()))!=11:raise SystemExit("Ellis officeholder uniqueness changed")
    methods={r["office_name"]:r["selection_method"] for r in roster}
    if methods["County Judge"]!="appointment" or any(value!="election" for office,value in methods.items() if office!="County Judge"):raise SystemExit("Ellis selection-method contract changed")
    forbidden={"County Attorney","District Attorney","Criminal District Attorney"}
    if forbidden & set(actual):raise SystemExit("Separate prosecutor office leaked into Ellis roster")
    if sum(r["office_name"]=="County and District Attorney" for r in roster)!=1:raise SystemExit("Expected one combined County and District Attorney")
    combined=rows(COMBINED)
    if len(combined)!=1 or combined[0]["current_officeholder"]!="Lindy Beaty":raise SystemExit("Combined-prosecutor evidence changed")
    for field in ("separate_county_attorney_row","separate_district_attorney_row","criminal_district_attorney_row"):
        if combined[0][field]!="FALSE":raise SystemExit(f"Combined-prosecutor split flag changed: {field}")
    non=rows(NON_SCOPE)
    for office in ("County Court at Law Judge","District Court Judge","Justice of the Peace","County Constable","County Auditor"):
        if not any(r["office_name"]==office for r in non):raise SystemExit(f"Missing non-scope evidence: {office}")
    sources=rows(MANIFEST)
    if len(sources)!=22:raise SystemExit(f"Expected 22 sources, found {len(sources)}")
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    if not contract["commissioner_identity_layer_url"].endswith("/MapServer/680") or contract["district_field"]!="Commissioner_Pct":raise SystemExit("Ellis GIS identity-layer contract changed")
    if contract["commissioner_precinct_count"]!=4 or contract["voting_precinct_count"]!=61:raise SystemExit("Ellis geography count changed")
    if contract["commissioner_source_voting_precinct_ids"]!=EXPECTED_GROUPS:raise SystemExit("Ellis Commissioner assignment changed")
    if contract["split_descendants"]!={"1060":{"district":"1","parent":"1006"},"1061":{"district":"3","parent":"1038"}}:raise SystemExit("Ellis split-parent contract changed")
    if contract["commissioner_adopted_at"]!="2021-11-30" or contract["commissioner_effective_at"]!="2023-01-01":raise SystemExit("Ellis Commissioner-plan dates changed")
    if contract["split_accepted_at"]!="2025-04-15" or contract["split_effective_at"]!="2026-01-01":raise SystemExit("Ellis split dates changed")
    if contract["interdistrict_overlap_area_degrees"]!=0 or contract["union_symmetric_difference_area_degrees"]!=0 or contract["all_voting_precincts_assigned"] is not True:raise SystemExit("Ellis topology contract changed")
def live():
    contracts=[
      ("https://www.elliscountytx.gov/128/County-Judge",("John Wray",)),
      ("https://www.co.ellis.tx.us/CivicAlerts.aspx?AID=1119",("John Wray","May 15 2025","November 2026")),
      ("https://www.elliscountytx.gov/Directory.aspx?did=46",("Randy Stinson","Lane Grayson","Louis Ponder","Kyle Butler")),
      ("https://www.elliscountytx.gov/directory.aspx?EID=220",("Brad Norman","Sheriff")),
      ("https://www.elliscountytx.gov/73/County-and-District-Attorney",("Lindy Beaty","felony","misdemeanor","legal advice")),
      ("https://www.elliscountytx.gov/74/County-Clerk",("Krystal Valdez",)),
      ("https://www.elliscountytx.gov/79/District-Clerk",("Melanie Reed",)),
      ("https://www.elliscountytx.gov/directory.aspx?EID=58",("Richard Rozier",)),
      ("https://www.elliscountytx.gov/78/County-Treasurer",("Cheryl Chambers",)),
      ("https://www.elliscountytx.gov/1072/Redistricting-Maps-20212025",("November 30 2021","January 1 2023","Precinct 1060","Precinct 1061","January 1 2026")),
    ]
    accessible=0
    for url,markers in contracts:
        page=fetch(url);accessible+=page is not None;require(page,url,markers)
    print(f"Validated {accessible} live Ellis County page contract(s).")
def main():committed();live();print("Ellis County roster, combined prosecutor, scope, and source contracts are valid.")
if __name__=="__main__":main()
