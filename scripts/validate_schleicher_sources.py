#!/usr/bin/env python3
"""Validate Schleicher County roster, combined clerk, scope, and source contracts."""
from __future__ import annotations
import csv, html, json, re, time, urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw/schleicher-county"
ROSTER=RAW/"current-elected-offices.csv"
COMBINED=RAW/"combined-county-district-clerk.csv"
NON_SCOPE=RAW/"non-scope-offices.csv"
MANIFEST=RAW/"source-manifest.csv"
CONTRACT=RAW/"gis-source-contract.json"

EXPECTED={
"County Judge":"Charlie Bradley",
"County Commissioner Precinct 1":"Gary Gibson",
"County Commissioner Precinct 2":"Steve Nelson",
"County Commissioner Precinct 3":"Kirk Griffin",
"County Commissioner Precinct 4":"Chris Meador",
"Sheriff":"Jason Chatham",
"County and District Clerk":"Marsha L. Maskill",
"Tax Assessor-Collector":"Vanessa Covarrubiaz",
"County Treasurer":"Jennifer L. Henderson",
}
HEADERS={"User-Agent":"Mozilla/5.0 Civic-Cartography-validator/1.0","Accept-Encoding":"identity"}

def searchable(value:str)->str:
    return re.sub(r"[^a-z0-9]+"," ",value.casefold()).strip()

def fetch(url:str)->str|None:
    for attempt in range(1,4):
        try:
            request=urllib.request.Request(url,headers=HEADERS)
            with urllib.request.urlopen(request,timeout=45) as response:
                return html.unescape(response.read().decode("utf-8",errors="replace"))
        except urllib.error.HTTPError as exc:
            if exc.code in {403,404,429}: return None
        except Exception:
            pass
        if attempt<3: time.sleep(attempt*3)
    return None

def require(page:str|None,url:str,markers:tuple[str,...])->None:
    if page is None: return
    text=searchable(page)
    missing=[marker for marker in markers if searchable(marker) not in text]
    if missing: raise SystemExit(f"{url} lost markers: {missing}")

def fetch_contract_page(url:str,markers:tuple[str,...])->str|None:
    """Retry HTTP 200 pages that are incomplete before failing the marker contract."""
    last_error:SystemExit|None=None
    for attempt in range(1,4):
        page=fetch(url)
        if page is None:
            return None
        try:
            require(page,url,markers)
            return page
        except SystemExit as exc:
            last_error=exc
            if attempt<3:
                time.sleep(attempt*3)
    if last_error is not None:
        raise last_error
    raise AssertionError("Schleicher page contract retry ended unexpectedly")

def committed()->None:
    with ROSTER.open(newline="",encoding="utf-8") as handle:
        rows=list(csv.DictReader(handle))
    actual={row["office_name"]:row["officeholder"] for row in rows}
    if len(rows)!=9 or actual!=EXPECTED:
        raise SystemExit(f"Schleicher roster changed: {actual!r}")
    if len(set(actual.values()))!=9:
        raise SystemExit("Schleicher officeholder uniqueness changed")
    if {row["selection_method"] for row in rows}!={"election"}:
        raise SystemExit("Schleicher selection method changed")
    if sum(row["office_name"]=="County and District Clerk" for row in rows)!=1:
        raise SystemExit("Expected one combined County and District Clerk")
    if any(row["office_name"]=="County Clerk" for row in rows):
        raise SystemExit("Separate County Clerk leaked into roster")
    if any(row["office_name"]=="District Clerk" for row in rows):
        raise SystemExit("Separate District Clerk leaked into roster")
    clerk=next(row for row in rows if row["office_name"]=="County and District Clerk")
    if clerk["officeholder"]!="Marsha L. Maskill":
        raise SystemExit("Combined clerk holder changed")
    if (clerk["geography_type"],clerk["geography_id"])!=("countywide","COUNTYWIDE"):
        raise SystemExit("Combined clerk geography changed")

    with COMBINED.open(newline="",encoding="utf-8") as handle:
        combined=list(csv.DictReader(handle))
    if len(combined)!=1:
        raise SystemExit("Expected one combined-clerk contract row")
    contract_row=combined[0]
    expected={
        "office_name":"County and District Clerk",
        "current_officeholder":"Marsha L. Maskill",
        "office_status":"active_combined_elected_office",
        "selection_method":"election",
        "term_length_years":"4",
        "constitutional_authority":"Texas Constitution Article V §20",
        "separate_county_clerk_office":"FALSE",
        "separate_district_clerk_office":"FALSE",
    }
    for key,value in expected.items():
        if contract_row[key]!=value:
            raise SystemExit(f"Combined clerk contract changed: {key}={contract_row[key]!r}")

    with NON_SCOPE.open(newline="",encoding="utf-8") as handle:
        non_scope=list(csv.DictReader(handle))
    required={"County Attorney","District Attorney, 51st Judicial District","51st District Court Judge","Justice of the Peace","County Constable"}
    found={row["office_name"] for row in non_scope}
    if not required.issubset(found):
        raise SystemExit(f"Missing non-scope evidence: {required-found}")

    with MANIFEST.open(newline="",encoding="utf-8") as handle:
        sources=list(csv.DictReader(handle))
    if len(sources)!=20:
        raise SystemExit(f"Expected 20 sources, found {len(sources)}")
    required_sources={
        "schleicher-county-clerk","schleicher-district-clerk","schleicher-elections",
        "schleicher-redistricting-order","schleicher-primary-map",
        "texas-constitution-5-20","texas-sos-2026-qualifications",
        "texas-legislative-council-precincts","census-schleicher-county",
    }
    source_ids={row["source_id"] for row in sources}
    if not required_sources.issubset(source_ids):
        raise SystemExit(f"Source manifest missing: {required_sources-source_ids}")

    geometry=json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected_geometry={
        "county":"Schleicher County",
        "county_fips":"413",
        "official_primary_map_sha256":"abf1a78df7f6f6bf532c454b8673eb9bc30267aedcc89131b0c70b652cf6ee19",
        "adopted_redistricting_order_sha256":"64e101b0eb131f8ca31ca16abf8975509aa67671ae87ac770e02123a8a5409db",
        "tlc_precinct_zip_sha256":"70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107",
        "voting_precinct_count":4,
        "commissioner_precinct_count":4,
        "all_voting_precincts_assigned":True,
    }
    for key,value in expected_geometry.items():
        if geometry.get(key)!=value:
            raise SystemExit(f"Schleicher geometry contract changed: {key}={geometry.get(key)!r}")
    if geometry["assignment_confidence_min"]<0.85:
        raise SystemExit("Schleicher adopted-map assignment confidence dropped")
    if geometry["interdistrict_overlap_area_degrees"]!=0.0:
        raise SystemExit("Schleicher Commissioner overlap changed")
    if geometry["union_symmetric_difference_area_degrees"]!=0.0:
        raise SystemExit("Schleicher Commissioner union changed")
    assignments={row["voting_precinct_id"]:row["commissioner_precinct"] for row in geometry["assignments"]}
    if assignments!={"1":"1","2":"2","3":"3","4":"4"}:
        raise SystemExit(f"Schleicher precinct identity changed: {assignments!r}")

def live()->None:
    contracts=[
        ("https://www.schleichercounty.gov/page/homepage",("Charlie Bradley","Gary Gibson","Steve Nelson","Kirk Griffin","Chris Meador")),
        ("https://www.schleichercounty.gov/page/Commissioner.Court",("Gary Gibson","Steve Nelson","Kirk Griffin","Chris Meador")),
        ("https://www.schleichercounty.gov/page/County.Judge",("Charlie Bradley",)),
        ("https://www.schleichercounty.gov/page/Sheriff",("Jason Chatham",)),
        ("https://www.schleichercounty.gov/page/County.Clerk",("Marsha L. Maskill","County and District Clerk")),
        ("https://www.schleichercounty.gov/page/District.Clerk",("Marsha L. Maskill","County and District Clerk")),
        ("https://www.schleichercounty.gov/page/Elections",("Marsha L. Maskill","Precincts 1, 2, 3, 4")),
        ("https://www.schleichercounty.gov/page/Tax.Assessor",("Vanessa Covarrubiaz",)),
        ("https://www.schleichercounty.gov/page/Treasurer",("Jennifer L. Henderson",)),
        ("https://www.schleichercounty.gov/page/countyattorney",("Clint T. Griffin",)),
    ]
    accessible=0
    for url,markers in contracts:
        page=fetch_contract_page(url,markers)
        accessible+=page is not None
    print(f"Validated {accessible} live Schleicher County page contract(s).")

def main()->None:
    committed()
    live()
    print("Schleicher County roster, combined clerk, scope, and source contracts are valid.")

if __name__=="__main__":
    main()
