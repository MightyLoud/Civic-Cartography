import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/hidalgo-county/current-elected-offices.csv"
BOARD = ROOT / "data/raw/hidalgo-county/current-drainage-district-board.csv"
MANIFEST = ROOT / "data/raw/hidalgo-county/source-manifest.csv"
CONTRACT = ROOT / "data/raw/hidalgo-county/portal-source-contract.json"
NORMALIZED = ROOT / "data/normalized/hidalgo_county_elected_offices.csv"
PRECINCTS = ROOT / "data/geojson/hidalgo_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/hidalgo_county_countywide.geojson"
OPERATIONAL_LAYER = "https://services9.arcgis.com/dwMDP55HTfoj4n1c/arcgis/rest/services/County_Commissioners_View/FeatureServer/0"


def test_hidalgo_county_dual_body_contract() -> None:
    expected = {
        "County Judge": "Richard F. Cortez",
        "County Commissioner Precinct 1": "David L. Fuentes",
        "County Commissioner Precinct 2": 'Eduardo "Eddie" Cantu',
        "County Commissioner Precinct 3": 'Everardo "Ever" Villarreal',
        "County Commissioner Precinct 4": "Ellie Torres",
        "Sheriff": 'J.E. "Eddie" Guerra',
        "County Clerk": "Arturo Guajardo, Jr.",
        "District Clerk": "Laura Hinojosa",
        "Tax Assessor-Collector": 'Pablo "Paul" Villarreal, Jr.',
        "County Treasurer": "Lita Leo",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 10
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert len({row["officeholder"] for row in evidence}) == 10
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}

    with BOARD.open(newline="", encoding="utf-8") as handle:
        board = list(csv.DictReader(handle))
    assert len(board) == 5
    assert {row["body_name"] for row in board} == {"Hidalgo County Drainage District No. 1"}
    assert [row["board_role"] for row in board].count("Chairman of the Board") == 1
    assert [row["board_role"] for row in board].count("Board Member") == 4
    court_offices = {
        "County Judge",
        "County Commissioner Precinct 1",
        "County Commissioner Precinct 2",
        "County Commissioner Precinct 3",
        "County Commissioner Precinct 4",
    }
    assert {row["source_office_name"] for row in board} == court_offices
    assert {row["geography_id"] for row in board} == {"COUNTYWIDE", "1", "2", "3", "4"}
    evidence_by_office = {row["office_name"]: row["officeholder"] for row in evidence}
    for row in board:
        assert evidence_by_office[row["source_office_name"]] == row["officeholder"]
        assert "not an additional elected office" in row["notes"]
    assert len(evidence) == 10  # Board assignments do not create five duplicate elected offices.

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 20
    assert "ten current elected offices" in manifest["hidalgo-county-officials"]["use"]
    assert "separate consecutive public meetings" in manifest["hidalgo-county-court-live"]["use"]
    assert "County Judge and four County Commissioners" in manifest["hidalgo-drainage-admin"]["use"]
    assert "1939" in manifest["hidalgo-drainage-history"]["use"]
    assert "November 13, 2021" in manifest["hidalgo-county-2021-redistricting"]["use"]
    arcgis_use = manifest["hidalgo-county-arcgis"]["use"]
    for value in ("rpresas", "County_Commissioners_View/FeatureServer/0", "DISTRICT"):
        assert value in arcgis_use

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["item_id"] == "bc95c6e0bbed4ba98a16b303219de88a"
    assert contract["item_title"] == "Hidalgo County Basemap"
    assert contract["item_owner"] == "rpresas"
    assert contract["operational_layer_url"] == OPERATIONAL_LAYER
    assert contract["district_field"] == "DISTRICT"
    assert contract["district_values"] == ["1", "2", "3", "4"]
    assert "county-associated" in contract["source_classification"]

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_type"] == "countywide")
    for office in ("County Judge", "Sheriff", "County Clerk", "District Clerk", "Tax Assessor-Collector", "County Treasurer"):
        assert office in countywide["office_name"]
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["geometry_source_url"] for row in commissioner_rows} == {OPERATIONAL_LAYER}
    assert all("Drainage District board service is not an additional elected office or geometry" in row["notes"] for row in commissioner_rows)

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:hidalgo:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "hidalgo-county-countywide"
    assert county_props["census_geoid"] == "48215"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        precinct_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["district_type"] == "commissioner_precinct"
        assert props["district_name"] == f"Commissioner Precinct {precinct_id}"
        assert props["source_layer"] == OPERATIONAL_LAYER
        assert props["source_district_field"] == "DISTRICT"
        assert str(attributes["DISTRICT"]) == precinct_id
        found[precinct_id] = props["geometry_id"]
    assert found == {
        "1": "hidalgo-county-commissioner-precinct-1",
        "2": "hidalgo-county-commissioner-precinct-2",
        "3": "hidalgo-county-commissioner-precinct-3",
        "4": "hidalgo-county-commissioner-precinct-4",
    }
