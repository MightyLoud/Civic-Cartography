import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/collin-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/collin-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/collin_county_commissioners_court.csv"
PRECINCTS = ROOT / "data/geojson/collin_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/collin_county_countywide.geojson"


def test_collin_county_stale_narrative_and_operational_gis_contract() -> None:
    expected = {
        "County Judge": "Chris Hill",
        "County Commissioner Precinct 1": "Susan Fletcher",
        "County Commissioner Precinct 2": "Cheryl Williams",
        "County Commissioner Precinct 3": "Darrell Hale",
        "County Commissioner Precinct 4": "Duncan Webb",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["officeholder"] for row in evidence}) == 5

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert all("2011/2012 dates are stale" in row["notes"] for row in commissioner_rows)
    assert all("November 1, 2021" in row["notes"] for row in commissioner_rows)

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 13
    stale = manifest["collin-county-stale-precinct-page"]["use"]
    assert "September 6, 2011" in stale
    assert "January 1, 2012" in stale
    current = manifest["collin-county-2021-commissioners-layer"]["use"]
    assert "November 1, 2021" in current
    assert "2021-1127-11-01" in current
    for field in ("COMMISH", "COMMISH_N"):
        assert field in current

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:collin:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "collin-county-countywide"
    assert county_props["census_geoid"] == "48085"

    expected_names = {
        "1": "Susan Fletcher",
        "2": "Cheryl Williams",
        "3": "Darrell Hale",
        "4": "Duncan Webb",
    }
    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        precinct_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["district_type"] == "commissioner_precinct"
        assert props["district_name"] == f"Commissioner Precinct {precinct_id}"
        assert props["source_district_field"] == "COMMISH"
        assert str(attributes["COMMISH"]) == precinct_id
        assert attributes["COMMISH_N"] == expected_names[precinct_id]
        found[precinct_id] = props["geometry_id"]
    assert found == {
        "1": "collin-county-commissioner-precinct-1",
        "2": "collin-county-commissioner-precinct-2",
        "3": "collin-county-commissioner-precinct-3",
        "4": "collin-county-commissioner-precinct-4",
    }
