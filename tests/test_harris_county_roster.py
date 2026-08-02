import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/harris-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/harris-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/harris_county_commissioners_court.csv"
PRECINCTS = ROOT / "data/geojson/harris_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/harris_county_countywide.geojson"


def test_harris_county_roster_and_geometry_contract() -> None:
    expected = {
        "County Judge": "Lina Hidalgo",
        "County Commissioner Precinct 1": "Rodney Ellis",
        "County Commissioner Precinct 2": "Adrian Garcia",
        "County Commissioner Precinct 3": "Tom S. Ramsey",
        "County Commissioner Precinct 4": "Lesley Briones",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    precinct_four = next(row for row in evidence if row["geography_id"] == "4")
    assert "legacy URL alias" in precinct_four["notes"]
    assert "stale-geometry" in precinct_four["notes"]

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 12
    assert "harris-county-current-precinct-layer" in manifest
    current_layer = manifest["harris-county-current-precinct-layer"]["use"]
    assert "PCT_NO" in current_layer
    assert "COMMISSION" in current_layer
    assert "legacy URL" in current_layer
    assert "harris-county-obsolete-2011-precinct-item" in manifest
    stale = manifest["harris-county-obsolete-2011-precinct-item"]["use"]
    assert "2011" in stale
    assert "stale-geometry" in stale
    assert "census-harris-county" in manifest

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:harris:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "harris-county-countywide"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    websites = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["source_district_field"] == "PCT_NO"
        assert str(attributes["PCT_NO"]) == district_id
        found[district_id] = attributes["COMMISSION"]
        websites[district_id] = attributes["URL"]
    assert found == {
        "1": "Rodney Ellis",
        "2": "Adrian Garcia",
        "3": "Tom S. Ramsey",
        "4": "Lesley Briones",
    }
    assert websites == {
        "1": "https://www.hcp1.net/",
        "2": "https://www.hcp2.com/",
        "3": "https://www.pct3.com/",
        "4": "https://www.hcp4.net/",
    }
