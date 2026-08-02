import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/dallas-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/dallas-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/dallas_county_commissioners_court.csv"
DISTRICTS = ROOT / "data/geojson/dallas_county_commissioner_districts.geojson"
COUNTY = ROOT / "data/geojson/dallas_county_countywide.geojson"


def test_dallas_county_district_nomenclature_and_roster_bearing_gis_contract() -> None:
    expected = {
        "County Judge": "Clay Jenkins",
        "County Commissioner District 1": "Dr. Theresa Daniel",
        "County Commissioner District 2": "Andy Sommerman",
        "County Commissioner District 3": "John Wiley Price",
        "County Commissioner District 4": "Dr. Elba Garcia",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    commissioner_evidence = [row for row in evidence if row["geography_type"] == "commissioner_precinct"]
    assert len(commissioner_evidence) == 4
    assert all("District" in row["office_name"] for row in commissioner_evidence)
    assert all("canonical geography type" in row["notes"] for row in commissioner_evidence)

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_type"] == "countywide")
    assert countywide["office_name"] == "County Judge"
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["district_name"] for row in commissioner_rows} == {
        "Commissioner District 1",
        "Commissioner District 2",
        "Commissioner District 3",
        "Commissioner District 4",
    }
    assert all("canonical geography type is commissioner_precinct" in row["notes"] for row in commissioner_rows)

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 13
    assert "dallas-county-government-overview" in manifest
    assert "divided into four districts" in manifest["dallas-county-government-overview"]["use"]
    assert "dallas-county-who-is-my-commissioner" in manifest
    assert "static Commissioner District map" in manifest["dallas-county-who-is-my-commissioner"]["use"]
    assert manifest["dallas-county-searchable-app"]["url"].endswith("929bdc6b485f47428f2e26266bd3ed81")
    assert "zqe2kwz79KUqUvxC" in manifest["dallas-county-searchable-app"]["use"]
    assert "a9d7fe8a050848ed9d5f08086436ed3f" in manifest["dallas-county-searchable-webmap"]["url"]
    layer = manifest["dallas-county-adopted-2021-layer"]["use"]
    for field in ("DISTRICT", "Name", "Comm_URL", "Photo"):
        assert field in layer
    assert "census-dallas-county" in manifest

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:dallas:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "dallas-county-countywide"
    assert county_props["census_geoid"] == "48113"

    expected_names = {
        "1": "Dr. Theresa Daniel",
        "2": "Andy Sommerman",
        "3": "John Wiley Price",
        "4": "Dr. Elba Garcia",
    }
    districts = json.loads(DISTRICTS.read_text(encoding="utf-8"))
    assert len(districts["features"]) == 4
    found = {}
    for feature in districts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["district_type"] == "commissioner_precinct"
        assert props["district_name"] == f"Commissioner District {district_id}"
        assert props["source_district_field"] == "DISTRICT"
        assert str(attributes["DISTRICT"]) == district_id
        assert attributes["Name"] == expected_names[district_id]
        assert attributes["Comm_URL"] == f"https://www.dallascounty.org/government/comcrt/district{district_id}/"
        assert attributes["Photo"] == f"COMM. DIST. {district_id}"
        found[district_id] = props["geometry_id"]
    assert found == {
        "1": "dallas-county-commissioner-district-1",
        "2": "dallas-county-commissioner-district-2",
        "3": "dallas-county-commissioner-district-3",
        "4": "dallas-county-commissioner-district-4",
    }
