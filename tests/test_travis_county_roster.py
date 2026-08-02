import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/travis-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/travis-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/travis_county_commissioners_court.csv"
PRECINCTS = ROOT / "data/geojson/travis_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/travis_county_countywide.geojson"


def test_travis_county_roster_and_geometry_contract() -> None:
    expected = {
        "County Judge": "Andy Brown",
        "County Commissioner Precinct 1": "Jeff Travillion",
        "County Commissioner Precinct 2": "Brigid Shea",
        "County Commissioner Precinct 3": "Ann Howard",
        "County Commissioner Precinct 4": "George Morales",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    precinct_four = next(row for row in evidence if row["geography_id"] == "4")
    assert "George Morales" in precinct_four["notes"]
    assert "Margaret Gomez" in precinct_four["notes"]
    assert "stale-source" in precinct_four["notes"]

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    precinct_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(precinct_rows) == 4
    assert {
        row["geometry_source_url"] for row in precinct_rows
    } == {
        "https://gis.traviscountytx.gov/server1/rest/services/"
        "Boundaries_and_Jurisdictions/Travis_County_Commissioner_Precincts/"
        "FeatureServer/0"
    }

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 12
    assert "travis-county-transparency-contacts" in manifest
    assert "Margaret Gomez" in manifest["travis-county-transparency-contacts"]["use"]
    assert "travis-county-commissioner-precincts-feature" in manifest
    assert "renderer" in manifest["travis-county-commissioner-precincts-feature"]["use"]
    assert "timeout" in manifest["travis-county-commissioner-precincts-feature"]["use"]
    assert "travis-county-commissioner-precincts-hub" in manifest
    assert "Margaret Gómez" in manifest["travis-county-commissioner-precincts-hub"]["use"]
    assert "census-travis-county" in manifest

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:travis:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "travis-county-countywide"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    stale_cache = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        assert props["source_district_field"] == "PRECINCT"
        assert str(props["source_attributes"]["PRECINCT"]) == district_id
        assert props["source_roster_metadata_url"].endswith("FeatureServer/0?f=json")
        found[district_id] = props["source_attributes"]["COMMISSIONER"]
        if "HUB_CACHE_COMMISSIONER" in props["source_attributes"]:
            stale_cache[district_id] = props["source_attributes"]["HUB_CACHE_COMMISSIONER"]
    assert found == {
        "1": "Jeff Travillion",
        "2": "Brigid Shea",
        "3": "Ann Howard",
        "4": "George Morales",
    }
    assert stale_cache == {"4": "Margaret Gómez"}
