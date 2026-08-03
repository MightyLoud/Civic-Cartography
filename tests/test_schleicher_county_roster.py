from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw/schleicher-county"
ROSTER=RAW/"current-elected-offices.csv"
COMBINED=RAW/"combined-county-district-clerk.csv"
NORMALIZED=ROOT/"data/normalized/schleicher_county_elected_offices.csv"
COUNTYWIDE=ROOT/"data/geojson/schleicher_county_countywide.geojson"
COMMISSIONERS=ROOT/"data/geojson/schleicher_county_commissioner_precincts.geojson"
EXPECTED_DIGEST="70575f6d635746024f155eb2598c9551a58a96fa6fa9e90b050bbb17702fd3bf"

def rows(path):
    with path.open(newline="",encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def features(path):
    return json.loads(path.read_text(encoding="utf-8"))["features"]

def test_schleicher_combined_clerk_release_contract():
    roster=rows(ROSTER)
    expected={
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
    assert len(roster)==9
    assert {row["office_name"]:row["officeholder"] for row in roster}==expected
    assert len({row["officeholder"] for row in roster})==9
    assert {row["selection_method"] for row in roster}=={"election"}
    assert sum(row["office_name"]=="County and District Clerk" for row in roster)==1
    assert not any(row["office_name"]=="County Clerk" for row in roster)
    assert not any(row["office_name"]=="District Clerk" for row in roster)

    combined=rows(COMBINED)
    assert len(combined)==1
    clerk=combined[0]
    assert clerk["current_officeholder"]=="Marsha L. Maskill"
    assert clerk["office_status"]=="active_combined_elected_office"
    assert clerk["selection_method"]=="election"
    assert clerk["term_length_years"]=="4"
    assert clerk["constitutional_authority"]=="Texas Constitution Article V §20"
    assert clerk["separate_county_clerk_office"]=="FALSE"
    assert clerk["separate_district_clerk_office"]=="FALSE"

    normalized=rows(NORMALIZED)
    assert len(normalized)==5
    assert {row["qa_status"] for row in normalized}=={"approved"}
    assert {row["parity_ok"] for row in normalized}=={"TRUE"}
    assert {row["district_id"] for row in normalized}=={"COUNTYWIDE","1","2","3","4"}
    countywide=next(row for row in normalized if row["district_type"]=="countywide")
    assert "County and District Clerk" in countywide["office_name"]
    assert "separate County Clerk and District Clerk rows are intentionally absent" in countywide["notes"]

    contract=json.loads((RAW/"gis-source-contract.json").read_text(encoding="utf-8"))
    assert contract["official_primary_map_sha256"]=="abf1a78df7f6f6bf532c454b8673eb9bc30267aedcc89131b0c70b652cf6ee19"
    assert contract["adopted_redistricting_order_sha256"]=="64e101b0eb131f8ca31ca16abf8975509aa67671ae87ac770e02123a8a5409db"
    assert contract["tlc_precinct_zip_sha256"]=="70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
    assert contract["voting_precinct_count"]==4
    assert contract["commissioner_precinct_count"]==4
    assert contract["all_voting_precincts_assigned"] is True
    assert contract["assignment_confidence_min"]>=0.85
    assert contract["interdistrict_overlap_area_degrees"]==0.0
    assert contract["union_symmetric_difference_area_degrees"]==0.0
    assert {row["voting_precinct_id"]:row["commissioner_precinct"] for row in contract["assignments"]}=={"1":"1","2":"2","3":"3","4":"4"}

    county=features(COUNTYWIDE)
    commissioners=features(COMMISSIONERS)
    assert len(county)==1
    assert county[0]["properties"]["census_geoid"]=="48413"
    assert len(commissioners)==4
    assert {str(feature["properties"]["district_id"]) for feature in commissioners}=={"1","2","3","4"}
    all_features=county+commissioners
    assert len(all_features)==5
    assert len({feature["properties"]["geometry_id"] for feature in all_features})==5
    assert len({feature["properties"]["record_id"] for feature in all_features})==5

    digest=hashlib.sha256()
    for path in sorted((COUNTYWIDE,COMMISSIONERS),key=lambda item:item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    assert digest.hexdigest()==EXPECTED_DIGEST
