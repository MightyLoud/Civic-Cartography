from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"data/raw/burnet-county/current-elected-offices.csv"
SEPARATION=ROOT/"data/raw/burnet-county/prosecutor-office-separation.csv"
NORMALIZED=ROOT/"data/normalized/burnet_county_elected_offices.csv"
COUNTYWIDE=ROOT/"data/geojson/burnet_county_countywide.geojson"
COMMISSIONERS=ROOT/"data/geojson/burnet_county_commissioner_precincts.geojson"
DA_AREA=ROOT/"data/geojson/burnet_33rd_424th_district_attorney_service_area.geojson"
EXPECTED_DIGEST="eef9a2b7386d2356aa60aa9cd9a17f077500265f3553ab99f82487a7c875542e"

def rows(path):
    with path.open(newline="",encoding="utf-8") as handle:return list(csv.DictReader(handle))
def features(path):return json.loads(path.read_text(encoding="utf-8"))["features"]

def test_burnet_county_release_contract():
    roster=rows(ROSTER)
    assert len(roster)==12
    assert len({r["officeholder"] for r in roster})==12
    assert sum(r["office_name"]=="County Attorney" for r in roster)==1
    assert sum(r["office_name"].startswith("District Attorney") for r in roster)==1
    assert not any("Criminal District Attorney" in r["office_name"] for r in roster)
    ca=next(r for r in roster if r["office_name"]=="County Attorney")
    da=next(r for r in roster if r["office_name"].startswith("District Attorney"))
    assert (ca["geography_type"],ca["geography_id"])==("countywide","COUNTYWIDE")
    assert (da["geography_type"],da["geography_id"])==("district_attorney_service_area","33-424")

    separation=rows(SEPARATION)
    assert len(separation)==2
    assert {r["current_officeholder"] for r in separation}=={"Eddie Arredondo","Perry Thomas"}
    da_sep=next(r for r in separation if r["current_officeholder"]=="Perry Thomas")
    assert da_sep["component_county_geoids"]=="48031; 48053; 48299; 48411"

    normalized=rows(NORMALIZED)
    assert len(normalized)==6
    assert {r["qa_status"] for r in normalized}=={"approved"}
    assert {r["parity_ok"] for r in normalized}=={"TRUE"}
    assert {r["district_type"] for r in normalized}=={"countywide","commissioner_precinct","district_attorney_service_area"}

    county=features(COUNTYWIDE);commissioners=features(COMMISSIONERS);da_features=features(DA_AREA)
    assert len(county)==1 and len(commissioners)==4 and len(da_features)==1
    assert {str(f["properties"]["district_id"]) for f in commissioners}=={"1","2","3","4"}
    props=da_features[0]["properties"]
    assert props["component_county_geoids"]==["48031","48053","48299","48411"]
    assert props["component_count"]==4

    all_features=county+commissioners+da_features
    assert len(all_features)==6
    assert len({f["properties"]["geometry_id"] for f in all_features})==6
    assert len({f["properties"]["record_id"] for f in all_features})==6

    digest=hashlib.sha256()
    for path in sorted((COUNTYWIDE,COMMISSIONERS,DA_AREA),key=lambda p:p.name):
        digest.update(path.name.encode());digest.update(b"\0");digest.update(path.read_bytes());digest.update(b"\0")
    assert digest.hexdigest()==EXPECTED_DIGEST
