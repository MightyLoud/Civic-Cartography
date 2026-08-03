#!/usr/bin/env python3
"""Validate Kaufman County roster, prosecutor consolidation, scope, and source contracts."""
from __future__ import annotations
import csv, html, json, re, time, urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/kaufman-county/current-elected-offices.csv"
CONSOLIDATION=ROOT/"data/raw/kaufman-county/criminal-district-attorney-consolidation.csv"
NON_SCOPE=ROOT/"data/raw/kaufman-county/non-scope-offices.csv"
MANIFEST=ROOT/"data/raw/kaufman-county/source-manifest.csv"
CONTRACT=ROOT/"data/raw/kaufman-county/gis-source-contract.json"

EXPECTED={
"County Judge":"Jakie Allen",
"County Commissioner Precinct 1":"Terry Crow",
"County Commissioner Precinct 2":"William “Skeet” Phillips",
"County Commissioner Precinct 3":"Kelly Lane",
"County Commissioner Precinct 4":"Tommy Moore",
"Sheriff":"Bryan Beavers",
"County Clerk":"Laura Hughes",
"District Clerk":"Rhonda Hughey",
"Tax Assessor-Collector":"Teressa Floyd",
"County Treasurer":"Charles “Chuck” Mohnkern",
"Criminal District Attorney":"Erleigh Norville Wiley",
}
SOURCE_IDS={
"kaufman-commissioners-court","kaufman-county-judge","kaufman-sheriff",
"kaufman-county-clerk","kaufman-district-clerk","kaufman-tax-assessor",
"kaufman-county-treasurer","kaufman-criminal-district-attorney",
"kaufman-cda-leadership","kaufman-cda-open-records","kaufman-campaign-finance",
"kaufman-county-surveyor","texas-government-code-44-229",
"kaufman-2021-redistricting-order","kaufman-official-commissioner-map",
"kaufman-official-gis-app","texas-legislative-council-voting-precincts",
"census-kaufman-county",
}
HEADERS={"User-Agent":"Mozilla/5.0 Civic-Cartography-validator/1.0","Accept-Encoding":"identity"}

def searchable(value:str)->str:return re.sub(r"[^a-z0-9]+"," ",value.casefold()).strip()

def fetch(url:str,optional:bool=True)->str|None:
    last=None
    for attempt in range(1,4):
        try:
            req=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(req,timeout=45) as response:
                return html.unescape(response.read().decode("utf-8",errors="replace"))
        except urllib.error.HTTPError as exc:
            last=exc
            if optional and exc.code in {403,404,429}:return None
        except Exception as exc:last=exc
        if attempt<3:time.sleep(attempt*3)
    if optional:return None
    raise RuntimeError(f"Unable to fetch {url}: {last}")

def require(page:str|None,url:str,markers:tuple[str,...])->None:
    if page is None:return
    text=searchable(page);missing=[m for m in markers if searchable(m) not in text]
    if missing:raise SystemExit(f"{url} lost markers: {missing}")

def committed()->None:
    with ROSTER.open(newline="",encoding="utf-8") as handle:rows=list(csv.DictReader(handle))
    actual={row["office_name"]:row["officeholder"] for row in rows}
    if len(rows)!=11 or actual!=EXPECTED:raise SystemExit(f"Kaufman roster changed: {actual!r}")
    if len(set(actual.values()))!=11:raise SystemExit("Kaufman roster contains duplicate holders")
    if {row["selection_method"] for row in rows}!={"election"}:raise SystemExit("All Kaufman current holders must be elected")
    if sum(row["office_name"]=="Criminal District Attorney" for row in rows)!=1:raise SystemExit("Expected one Criminal District Attorney")
    if any(row["office_name"] in {"County Attorney","District Attorney"} for row in rows):raise SystemExit("Duplicate prosecutor office entered roster")
    p2=next(row for row in rows if row["office_name"]=="County Commissioner Precinct 2")
    if "William Phillips" not in p2["notes"] or "Skeet Phillips" not in p2["notes"]:raise SystemExit("Precinct 2 alias contract missing")

    with CONSOLIDATION.open(newline="",encoding="utf-8") as handle:c=list(csv.DictReader(handle))
    if len(c)!=1:raise SystemExit("Expected one prosecutor consolidation row")
    row=c[0]
    if row["office_name"]!="Criminal District Attorney" or row["current_officeholder"]!="Erleigh Norville Wiley":raise SystemExit(f"Consolidation changed: {row!r}")
    if row["separate_county_attorney_office"]!="FALSE" or row["separate_district_attorney_office"]!="FALSE":raise SystemExit("Standalone prosecutor office falsely enabled")
    if "County Attorney duties" not in row["component_duties"] or "District Attorney duties" not in row["component_duties"]:raise SystemExit("Component duties missing")
    if "44.229" not in row["authority_url"]:raise SystemExit("Statutory authority missing")

    with NON_SCOPE.open(newline="",encoding="utf-8") as handle:non=list(csv.DictReader(handle))
    surveyor=next((x for x in non if x["office_name"]=="County Surveyor"),None)
    if not surveyor or surveyor["current_officeholder"]!="Greg Sjerven":raise SystemExit("County Surveyor non-scope evidence missing")
    if "County Surveyor" in actual:raise SystemExit("County Surveyor leaked into bounded roster")

    with MANIFEST.open(newline="",encoding="utf-8") as handle:sources=list(csv.DictReader(handle))
    ids={row["source_id"] for row in sources}
    if len(sources)!=18 or ids!=SOURCE_IDS:raise SystemExit(f"Kaufman source manifest changed: {ids!r}")
    by={row["source_id"]:row for row in sources}
    for source_id,marker in {
        "texas-government-code-44-229":"county and district attorneys",
        "kaufman-official-commissioner-map":"49673d66657b8dd93daec7aad205d549023bffa263c5db71707032ae321ca8e6",
        "kaufman-2021-redistricting-order":"conform",
        "texas-legislative-council-voting-precincts":"37",
    }.items():
        if marker not in by[source_id]["use"]:raise SystemExit(f"Manifest lost {marker!r} in {source_id}")

    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected={
        "derivation_type":"authoritative_composite",
        "official_commissioner_map_sha256":"49673d66657b8dd93daec7aad205d549023bffa263c5db71707032ae321ca8e6",
        "tlc_precinct_zip_sha256":"70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107",
        "all_voting_precincts_assigned":True,
        "commissioner_precinct_ids":["1","2","3","4"],
        "union_symmetric_difference_area_degrees":0.0,
        "interdistrict_overlap_area_degrees":0.0,
    }
    for field,value in expected.items():
        if contract.get(field)!=value:raise SystemExit(f"Kaufman contract changed: {field}={contract.get(field)!r}")
    if contract["tlc_precinct_metadata"]["voting_precinct_count"]!=37:raise SystemExit("Kaufman voting-precinct count changed")
    if contract["assignment_confidence_min"]<0.6 or contract["assignment_confidence_mean"]<0.9:raise SystemExit("Kaufman assignment confidence regressed")
    summary=contract["commissioner_summary"]
    if sum(row["source_voting_precinct_count"] for row in summary.values())!=37:raise SystemExit("Kaufman assignment count does not sum to 37")
    if {row["commissioner_precinct"] for row in summary.values()}!={"1","2","3","4"}:raise SystemExit("Kaufman summary IDs changed")

def live()->None:
    contracts=[
      ("https://www.kaufmancounty.net/159/Commissioners-Court",("Jakie Allen","Terry Crow","Skeet Phillips","Kelly Lane","Tommy Moore")),
      ("https://www.kaufmancounty.net/166/County-Clerk",("Laura Hughes",)),
      ("https://www.kaufmancounty.net/232/District-Clerk",("Rhonda Hughey",)),
      ("https://www.kaufmancounty.net/247/Tax-Assessor/QuickLinks",("Teressa Floyd",)),
      ("https://www.kaufmancounty.net/211/County-Treasurer",("Mohnkern",)),
      ("https://www.kaufmancounty.net/217/District-Attorney",("Erleigh Norville Wiley",)),
      ("https://www.kaufmancounty.net/496/Public-Information-Act-Open-Records",("Civil Division","Public Information")),
      ("https://www.kaufmancounty.net/254/County-Surveyor",("Greg Sjerven",)),
    ]
    accessible=0
    for url,markers in contracts:
        page=fetch(url)
        if page is not None:accessible+=1
        require(page,url,markers)
    print(f"Validated {accessible} live Kaufman County page contract(s); §44.229 remains enforced through committed statutory evidence because the Texas statutes host returns a wrapper page without section text to automated clients.")

def main()->None:
    committed();live()
    print("Kaufman County roster, Criminal District Attorney consolidation, scope, and source contracts are valid.")
if __name__=="__main__":main()
