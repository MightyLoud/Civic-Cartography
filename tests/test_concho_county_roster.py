from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/concho-county/current-elected-offices.csv";COMBINED=ROOT/"data/raw/concho-county/combined-office-structure.csv";NORMALIZED=ROOT/"data/normalized/concho_county_elected_offices.csv";COUNTYWIDE=ROOT/"data/geojson/concho_county_countywide.geojson";COMMISSIONERS=ROOT/"data/geojson/concho_county_commissioner_precincts.geojson";EXPECTED_DIGEST="3836eb848201930578016b63397e9d0ad5678639c49fa144a6c02f234389b626"
def rows(path):
    with path.open(newline="",encoding="utf-8") as h:return list(csv.DictReader(h))
def features(path):return json.loads(path.read_text(encoding="utf-8"))["features"]
def test_concho_county_release_contract():
    roster=rows(ROSTER);assert len(roster)==8;assert len({r["officeholder"] for r in roster})==8;assert {r["selection_method"] for r in roster}=={"election"}
    names={r["office_name"] for r in roster};assert "Sheriff/Tax Assessor-Collector" in names;assert "County/District Clerk" in names;assert not ({"Sheriff","Tax Assessor-Collector","County Clerk","District Clerk"}&names)
    combined=rows(COMBINED);assert len(combined)==2;assert {r["current_officeholder"] for r in combined}=={"Brent Frazier","Amber Hall"};assert {r["separate_component_rows"] for r in combined}=={"FALSE"}
    normalized=rows(NORMALIZED);assert len(normalized)==5;assert {r["qa_status"] for r in normalized}=={"approved"};assert {r["parity_ok"] for r in normalized}=={"TRUE"};assert {r["district_type"] for r in normalized}=={"countywide","commissioner_precinct"}
    county=features(COUNTYWIDE);commissioners=features(COMMISSIONERS);assert len(county)==1 and len(commissioners)==4;assert {str(f["properties"]["district_id"]) for f in commissioners}=={"1","2","3","4"}
    all_features=county+commissioners;assert len(all_features)==5;assert len({f["properties"]["geometry_id"] for f in all_features})==5;assert len({f["properties"]["record_id"] for f in all_features})==5
    expected={"1":["101","102"],"2":["203","204","205"],"3":["306"],"4":["407","408"]}
    assert {str(f["properties"]["district_id"]):f["properties"]["source_attributes"]["source_voting_precinct_ids"] for f in commissioners}==expected
    digest=hashlib.sha256()
    for path in sorted((COUNTYWIDE,COMMISSIONERS),key=lambda p:p.name):digest.update(path.name.encode());digest.update(b"\0");digest.update(path.read_bytes());digest.update(b"\0")
    assert digest.hexdigest()==EXPECTED_DIGEST
