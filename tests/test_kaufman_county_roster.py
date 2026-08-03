import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/kaufman-county/current-elected-offices.csv"
CONSOLIDATION=ROOT/"data/raw/kaufman-county/criminal-district-attorney-consolidation.csv"
NON_SCOPE=ROOT/"data/raw/kaufman-county/non-scope-offices.csv"
MANIFEST=ROOT/"data/raw/kaufman-county/source-manifest.csv"
NORMALIZED=ROOT/"data/normalized/kaufman_county_elected_offices.csv"
PRECINCTS=ROOT/"data/geojson/kaufman_county_commissioner_precincts.geojson"
COUNTY=ROOT/"data/geojson/kaufman_county_countywide.geojson"
CONTRACT=ROOT/"data/raw/kaufman-county/gis-source-contract.json"
DIGEST="50a46300a55671c29268ddfbae11cac3a8e189c02ff8b8f6754211b920be250b"

def test_kaufman_county_criminal_district_attorney_and_geometry_contract()->None:
    expected={
      "County Judge":"Jakie Allen","County Commissioner Precinct 1":"Terry Crow",
      "County Commissioner Precinct 2":"William “Skeet” Phillips","County Commissioner Precinct 3":"Kelly Lane",
      "County Commissioner Precinct 4":"Tommy Moore","Sheriff":"Bryan Beavers","County Clerk":"Laura Hughes",
      "District Clerk":"Rhonda Hughey","Tax Assessor-Collector":"Teressa Floyd",
      "County Treasurer":"Charles “Chuck” Mohnkern","Criminal District Attorney":"Erleigh Norville Wiley",
    }
    with ROSTER.open(newline="",encoding="utf-8") as h:roster=list(csv.DictReader(h))
    assert len(roster)==11
    assert {x["office_name"]:x["officeholder"] for x in roster}==expected
    assert len({x["officeholder"] for x in roster})==11
    assert {x["selection_method"] for x in roster}=={"election"}
    assert sum(x["office_name"]=="Criminal District Attorney" for x in roster)==1
    assert not any(x["office_name"] in {"County Attorney","District Attorney"} for x in roster)

    with CONSOLIDATION.open(newline="",encoding="utf-8") as h:con=list(csv.DictReader(h))
    assert len(con)==1
    assert con[0]["separate_county_attorney_office"]=="FALSE"
    assert con[0]["separate_district_attorney_office"]=="FALSE"
    assert "44.229" in con[0]["authority_url"]
    assert "County Attorney duties" in con[0]["component_duties"]
    assert "District Attorney duties" in con[0]["component_duties"]

    with NON_SCOPE.open(newline="",encoding="utf-8") as h:non=list(csv.DictReader(h))
    assert any(x["office_name"]=="County Surveyor" and x["current_officeholder"]=="Greg Sjerven" for x in non)

    with MANIFEST.open(newline="",encoding="utf-8") as h:sources=list(csv.DictReader(h))
    assert len(sources)==18

    with NORMALIZED.open(newline="",encoding="utf-8") as h:rows=list(csv.DictReader(h))
    assert len(rows)==5
    assert {x["district_id"] for x in rows}=={"COUNTYWIDE","1","2","3","4"}
    assert {x["qa_status"] for x in rows}=={"approved"}
    assert {x["parity_ok"] for x in rows}=={"TRUE"}
    countywide=next(x for x in rows if x["district_type"]=="countywide")
    assert countywide["office_name"]==("County Judge + Sheriff + County Clerk + District Clerk + "
      "Tax Assessor-Collector + County Treasurer + Criminal District Attorney")
    assert "no duplicate prosecutor office" in countywide["notes"]

    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["derivation_type"]=="authoritative_composite"
    assert contract["all_voting_precincts_assigned"] is True
    assert contract["tlc_precinct_metadata"]["voting_precinct_count"]==37
    assert contract["assignment_confidence_min"]>=0.6
    assert contract["assignment_confidence_mean"]>=0.9
    assert contract["union_symmetric_difference_area_degrees"]==0.0
    assert contract["interdistrict_overlap_area_degrees"]==0.0
    assert sum(x["source_voting_precinct_count"] for x in contract["commissioner_summary"].values())==37

    county=json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"])==1
    assert county["features"][0]["properties"]["record_id"]=="TX:county:kaufman:countywide:COUNTYWIDE"
    precincts=json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"])==4
    assert {x["properties"]["district_id"] for x in precincts["features"]}=={"1","2","3","4"}
    assert {x["properties"]["source_district_field"] for x in precincts["features"]}=={"official_map_color_assignment"}
    assert sum(x["properties"]["source_attributes"]["source_voting_precinct_count"] for x in precincts["features"])==37

    digest=hashlib.sha256()
    for path in sorted((COUNTY,PRECINCTS),key=lambda p:p.name):
        digest.update(path.name.encode("utf-8"));digest.update(b"\0");digest.update(path.read_bytes());digest.update(b"\0")
    assert digest.hexdigest()==DIGEST
