import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw/gillespie-county"
NORMALIZED=ROOT/"data/normalized/gillespie_county_elected_offices.csv"
COUNTY=ROOT/"data/geojson/gillespie_county_countywide.geojson"
PRECINCTS=ROOT/"data/geojson/gillespie_county_commissioner_precincts.geojson"

def test_gillespie_county_surveyor_and_geometry_contract():
    expected={"County Judge":"Daniel Jones","County Commissioner Precinct 1":"Charles Olfers","County Commissioner Precinct 2":"Keith Kramer","County Commissioner Precinct 3":"Charles “Chuck” Jenschke","County Commissioner Precinct 4":"Don Weinheimer","Sheriff":"Christopher “Chris” Ayala","County Clerk":"Lindsey Brown","District Clerk":"McKenna Monk Herbort","Tax Assessor-Collector":"Carol Rode Durst","County Treasurer":"Vicki J. Schmidt","County Surveyor":"Don Kuhlmann, RPLS"}
    with (RAW/"current-elected-offices.csv").open(newline="",encoding="utf-8") as h:roster=list(csv.DictReader(h))
    assert len(roster)==11
    assert {r["office_name"]:r["officeholder"] for r in roster}==expected
    assert len({r["officeholder"] for r in roster})==11
    assert {r["selection_method"] for r in roster}=={"election"}
    assert sum(r["office_name"]=="County Surveyor" for r in roster)==1
    assert not any(r["office_name"]=="County Engineer" for r in roster)
    with (RAW/"county-surveyor-office.csv").open(newline="",encoding="utf-8") as h:structure=list(csv.DictReader(h))
    assert len(structure)==1
    surveyor=structure[0]
    assert surveyor["current_officeholder"]=="Don Kuhlmann, RPLS"
    assert surveyor["office_status"]=="active_elected_office"
    assert surveyor["selection_method"]=="election"
    assert surveyor["term_length_years"]=="4"
    assert surveyor["qualification"]=="Registered Professional Land Surveyor"
    assert surveyor["separate_county_engineer"]=="TRUE"
    assert "future-election evidence only" in surveyor["future_candidate_evidence"]
    with (RAW/"non-scope-offices.csv").open(newline="",encoding="utf-8") as h:non=list(csv.DictReader(h))
    engineer=next(r for r in non if r["office_name"]=="County Engineer")
    assert "Melissa Eckert" in engineer["current_officeholder"]
    with NORMALIZED.open(newline="",encoding="utf-8") as h:normalized=list(csv.DictReader(h))
    assert len(normalized)==5
    assert {r["qa_status"] for r in normalized}=={"approved"}
    assert {r["parity_ok"] for r in normalized}=={"TRUE"}
    assert {r["district_id"] for r in normalized}=={"COUNTYWIDE","1","2","3","4"}
    countywide=next(r for r in normalized if r["district_type"]=="countywide")
    assert "County Surveyor" in countywide["office_name"] and "Don Kuhlmann" in countywide["notes"]
    contract=json.loads((RAW/"gis-source-contract.json").read_text(encoding="utf-8"))
    assert contract["official_commissioner_map_sha256"]=="5409b6592515efe37af4bbff12a2923e782794f2bbc4d077035a8f0163f3fd70"
    assert contract["tlc_precinct_zip_sha256"]=="70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
    assert contract["all_voting_precincts_assigned"] is True
    assert contract["assignment_confidence_min"]==0.92
    assert contract["tlc_precinct_metadata"]["voting_precinct_count"]==13
    assert contract["union_symmetric_difference_area_degrees"]==0.0
    assert contract["interdistrict_overlap_area_degrees"]==0.0
    assert {k:v["source_voting_precinct_count"] for k,v in contract["commissioner_summary"].items()}=={"1":3,"2":4,"3":3,"4":3}
    county=json.loads(COUNTY.read_text(encoding="utf-8"));assert len(county["features"])==1
    assert county["features"][0]["properties"]["census_geoid"]=="48171"
    precincts=json.loads(PRECINCTS.read_text(encoding="utf-8"));assert len(precincts["features"])==4
    assert {str(f["properties"]["district_id"]) for f in precincts["features"]}=={"1","2","3","4"}
    digest=hashlib.sha256()
    for path in sorted((COUNTY,PRECINCTS),key=lambda item:item.name):
        digest.update(path.name.encode("utf-8"));digest.update(b"\0");digest.update(path.read_bytes());digest.update(b"\0")
    assert digest.hexdigest()=="e1d5a045812bf990b084219fef6b145d551d1ecf05414ca639a26d0303bbce76"
