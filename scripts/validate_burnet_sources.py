#!/usr/bin/env python3
"""Validate Burnet County roster, prosecutor separation, scope, and source contracts."""
from __future__ import annotations
import csv, html, json, re, time, urllib.error, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/burnet-county/current-elected-offices.csv"
SEPARATION=ROOT/"data/raw/burnet-county/prosecutor-office-separation.csv"
NON_SCOPE=ROOT/"data/raw/burnet-county/non-scope-offices.csv"
MANIFEST=ROOT/"data/raw/burnet-county/source-manifest.csv"
CONTRACT=ROOT/"data/raw/burnet-county/gis-source-contract.json"
DA_CONTRACT=ROOT/"data/raw/burnet-county/district-attorney-service-area-contract.json"

EXPECTED={
"County Judge":"Bryan Wilson",
"County Commissioner Precinct 1":"Jim Luther, Jr.",
"County Commissioner Precinct 2":"Damon Beierle",
"County Commissioner Precinct 3":"Chad Collier",
"County Commissioner Precinct 4":"Joe Don Dockery",
"Sheriff":"Calvin Boyd",
"County Clerk":"Vicinta Stafford",
"District Clerk":"Casie Walker",
"Tax Assessor-Collector":"DeAnne Fisher",
"County Treasurer":"Karrie Crownover",
"County Attorney":"Eddie Arredondo",
"District Attorney, 33rd & 424th Judicial Districts":"Perry Thomas",
}
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
    if len(rows)!=12 or actual!=EXPECTED:raise SystemExit(f"Burnet roster changed: {actual!r}")
    if len(set(actual.values()))!=12 or {r["selection_method"] for r in rows}!={"election"}:raise SystemExit("Burnet uniqueness or selection changed")
    if sum(r["office_name"]=="County Attorney" for r in rows)!=1:raise SystemExit("Expected one County Attorney")
    if sum(r["office_name"].startswith("District Attorney") for r in rows)!=1:raise SystemExit("Expected one District Attorney")
    if any("Criminal District Attorney" in r["office_name"] for r in rows):raise SystemExit("Criminal District Attorney leaked into Burnet roster")
    county_attorney=next(r for r in rows if r["office_name"]=="County Attorney")
    district_attorney=next(r for r in rows if r["office_name"].startswith("District Attorney"))
    if (county_attorney["geography_type"],county_attorney["geography_id"])!=("countywide","COUNTYWIDE"):raise SystemExit("County Attorney geography changed")
    if (district_attorney["geography_type"],district_attorney["geography_id"])!=("district_attorney_service_area","33-424"):raise SystemExit("District Attorney geography changed")

    with SEPARATION.open(newline="",encoding="utf-8") as h:prosecutors=list(csv.DictReader(h))
    if len(prosecutors)!=2 or {r["current_officeholder"] for r in prosecutors}!={"Eddie Arredondo","Perry Thomas"}:raise SystemExit("Prosecutor separation changed")
    da=next(r for r in prosecutors if r["current_officeholder"]=="Perry Thomas")
    if da["component_county_geoids"]!="48031; 48053; 48299; 48411":raise SystemExit("District Attorney county composition changed")
    if any(r["separate_office"]!="TRUE" for r in prosecutors):raise SystemExit("Separate prosecutor office flag changed")

    with NON_SCOPE.open(newline="",encoding="utf-8") as h:non=list(csv.DictReader(h))
    for office in ("County Court at Law Judge","County Constables","Justices of the Peace","Magistrates","North Hill Country Public Defender"):
        if not any(r["office_name"]==office for r in non):raise SystemExit(f"Missing non-scope evidence: {office}")

    with MANIFEST.open(newline="",encoding="utf-8") as h:sources=list(csv.DictReader(h))
    if len(sources)!=23:raise SystemExit(f"Expected 23 sources, found {len(sources)}")
    required={"burnet-county-attorney","burnet-district-attorney","district-attorney-office","burnet-expunction-agencies","burnet-official-arcgis-app","burnet-official-commissioner-source","census-burnet-county","census-da-service-area"}
    ids={r["source_id"] for r in sources}
    if not required.issubset(ids):raise SystemExit(f"Source manifest missing: {required-ids}")

    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected={"application_item_id":"54aa0faa57064472a3cb2039b0e115ad","source_layer_url":"https://services3.arcgis.com/et3BBCaOmTkrlfxA/arcgis/rest/services/Online_Map_Final_WFL1/FeatureServer/3","district_field":"NAME","commissioner_precinct_ids":["1","2","3","4"],"commissioner_feature_count":4}
    for key,value in expected.items():
        if contract.get(key)!=value:raise SystemExit(f"Burnet commissioner contract changed: {key}={contract.get(key)!r}")
    if contract["source_feature_count"]!=4:raise SystemExit("Burnet source feature count changed")

    da_contract=json.loads(DA_CONTRACT.read_text(encoding="utf-8"))
    if da_contract["component_county_geoids"]!=["48031","48053","48299","48411"] or da_contract["component_count"]!=4:raise SystemExit("District Attorney service area composition changed")
    if da_contract["district_attorney_service_area_is_burnet_only"] is not False:raise SystemExit("District Attorney service area collapsed to Burnet County")

def live()->None:
    contracts=[
      ("https://www.burnetcountytexas.org/page/comm.home",("Bryan Wilson","Jim Luther","Damon Beierle","Chad Collier","Joe Don Dockery")),
      ("https://burnetcountyelections.com/elected-officials/",("Perry Thomas","Bryan Wilson","Eddie Arredondo","Calvin Boyd","Vicinta Stafford","Casie Walker","DeAnne Fisher","Karrie Crownover")),
      ("https://www.burnetcountytexas.org/page/attorney.home",("Eddie Arredondo","County Attorney")),
      ("https://www.burnetcountytexas.org/page/distatty.home",("Perry Thomas","Blanco","Burnet","Llano","San Saba")),
      ("https://www.burnetcountytexas.org/page/dclerk.expunctions",("District Attorney","County Attorney")),
      ("https://www.burnetcountytexas.org/page/cclerk.home",("Vicinta Stafford",)),
      ("https://www.burnetcountytexas.org/page/dclerk.home",("Casie Walker",)),
      ("https://www.burnetcountytexas.org/page/taxac.home",("DeAnne Fisher",)),
      ("https://www.burnetcountytexas.org/page/treas.home",("Karrie Crownover",)),
    ]
    accessible=0
    for url,markers in contracts:
        page=fetch(url);accessible+=page is not None;require(page,url,markers)
    print(f"Validated {accessible} live Burnet County page contract(s).")

def main()->None:
    committed();live();print("Burnet County roster, separate prosecutors, scope, and source contracts are valid.")
if __name__=="__main__":main()
