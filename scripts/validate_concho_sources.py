#!/usr/bin/env python3
"""Validate Concho County roster, dual combined offices, scope, and sources."""
from __future__ import annotations
import csv, html, json, re, time, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/concho-county/current-elected-offices.csv";COMBINED=ROOT/"data/raw/concho-county/combined-office-structure.csv";NON_SCOPE=ROOT/"data/raw/concho-county/non-scope-offices.csv";MANIFEST=ROOT/"data/raw/concho-county/source-manifest.csv";CONTRACT=ROOT/"data/raw/concho-county/gis-source-contract.json"
EXPECTED={"County Judge":"David Dillard","County Commissioner Precinct 1":"Trey Bradshaw","County Commissioner Precinct 2":"Eric Gully","County Commissioner Precinct 3":"Chad Miller","County Commissioner Precinct 4":"Keith Dillard","Sheriff/Tax Assessor-Collector":"Brent Frazier","County/District Clerk":"Amber Hall","County Treasurer":"Jenifer Gierisch"}
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
            if exc.code in {403,404,429}:return None
        except Exception:pass
        if attempt<3:time.sleep(attempt*3)
    return None
def require(page,url,markers):
    if page is None:return
    text=searchable(page);missing=[m for m in markers if searchable(m) not in text]
    if missing:raise SystemExit(f"{url} lost markers: {missing}")
def committed():
    roster=rows(ROSTER);actual={r["office_name"]:r["officeholder"] for r in roster}
    if len(roster)!=8 or actual!=EXPECTED:raise SystemExit(f"Concho roster changed: {actual!r}")
    if len(set(actual.values()))!=8 or {r["selection_method"] for r in roster}!={"election"}:raise SystemExit("Concho uniqueness or selection changed")
    component_names={"Sheriff","Tax Assessor-Collector","County Clerk","District Clerk"}
    if component_names & set(actual):raise SystemExit("Separate component office leaked into Concho roster")
    if sum(r["office_name"]=="Sheriff/Tax Assessor-Collector" for r in roster)!=1:raise SystemExit("Expected one combined sheriff/tax office")
    if sum(r["office_name"]=="County/District Clerk" for r in roster)!=1:raise SystemExit("Expected one combined clerk office")
    combined=rows(COMBINED)
    if len(combined)!=2 or {r["current_officeholder"] for r in combined}!={"Brent Frazier","Amber Hall"}:raise SystemExit("Combined-office evidence changed")
    if any(r["separate_component_rows"]!="FALSE" for r in combined):raise SystemExit("Combined-office split flag changed")
    non=rows(NON_SCOPE)
    for office in ("County Attorney","District Attorney","District Court Judge","Justice of the Peace","County Constable"):
        if not any(r["office_name"]==office for r in non):raise SystemExit(f"Missing non-scope evidence: {office}")
    sources=rows(MANIFEST)
    if len(sources)!=20:raise SystemExit(f"Expected 20 sources, found {len(sources)}")
    stale=next((r for r in sources if r["source_id"]=="sos-tax-directory-stale"),None)
    if not stale or stale["authority"]!="official_stale" or "Chad Miller" not in stale["notes"]:raise SystemExit("Stale SOS record contract changed")
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected_ids=["101","102","203","204","205","306","407","408"]
    if contract["voting_precinct_ids"]!=expected_ids or contract["commissioner_precinct_count"]!=4 or contract["voting_precinct_count"]!=8:raise SystemExit("Concho geometry contract changed")
    if contract["commissioner_assignments"]!={value:value[0] for value in expected_ids}:raise SystemExit("Concho Commissioner assignments changed")
    if contract["interdistrict_overlap_area_degrees"]!=0 or contract["union_symmetric_difference_area_degrees"]!=0:raise SystemExit("Concho geometry topology changed")
def live():
    contracts=[
      ("https://www.co.concho.tx.us/page/concho.Elections",("David Dillard","Trey Bradshaw","Eric Gully","Chad Miller","Keith Dillard","Brent Frazier","Jenifer Gierisch","Amber Hall","Sheriff Tax Assessor Collector","County District Clerk")),
      ("https://www.co.concho.tx.us/page/concho.commissioners.court",("Trey Bradshaw","Eric Gully","Chad Miller","Keith Dillard","Concho County Commissioner Precinct Map")),
      ("https://www.co.concho.tx.us/page/concho.Sheriff",("Sheriff Brent Frazier",)),
      ("https://www.co.concho.tx.us/page/concho.County.Assessor.Collector",("Brent Frazier","Tax Assessor Collector")),
      ("https://www.co.concho.tx.us/page/concho.County.Clerk",("Amber Hall","County and District Clerk")),
      ("https://www.co.concho.tx.us/page/concho.County.Treasurer",("Jenifer Gierisch",)),
      ("https://www.co.concho.tx.us/page/concho.County.Judge",("David Dillard",)),
      ("https://www.txdmv.gov/find-your-local-tax-office-dmv/by-county/Concho",("Brent Frazier",)),
      ("https://comptroller.texas.gov/taxes/property-tax/county-directory/concho.php",("Brent Frazier",)),
    ]
    accessible=0
    for url,markers in contracts:
        page=fetch(url);accessible+=page is not None;require(page,url,markers)
    print(f"Validated {accessible} live Concho County page contract(s).")
def main():committed();live();print("Concho County roster, combined offices, scope, and source contracts are valid.")
if __name__=="__main__":main()
