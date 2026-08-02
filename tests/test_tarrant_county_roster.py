import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/tarrant-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/tarrant-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/tarrant_county_commissioners_court.csv"
PRECINCTS = ROOT / "data/geojson/tarrant_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/tarrant_county_countywide.geojson"


def test_tarrant_county_roster_geometry_and_source_conflict_contract() -> None:
    expected = {
        "County Judge": "Tim O’Hare",
        "County Commissioner Precinct 1": "Roderick Miles Jr.",
        "County Commissioner Precinct 2": "Alisa Simmons",
        "County Commissioner Precinct 3": "Matt Krause",
        "County Commissioner Precinct 4": "Manny Ramirez",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    evidence_text = " ".join(row["officeholder"] for row in evidence)
    assert "Roy C. Brooks" not in evidence_text
    assert "Gary Fickes" not in evidence_text

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert {row["geometry_source_url"] for row in commissioner_rows} == {
        "https://mapit.tarrantcounty.com/arcgis/rest/services/BondProject/BondProjects/MapServer/3"
    }
    assert all("June 3, 2025" in row["notes"] for row in commissioner_rows)

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 13
    assert "tarrant-county-effective-2025-precinct-layer" in manifest
    controlling = manifest["tarrant-county-effective-2025-precinct-layer"]["use"]
    assert "June 3, 2025" in controlling
    assert "District_N" in controlling
    assert "tarrant-county-undated-general-precinct-layer" in manifest
    lagging = manifest["tarrant-county-undated-general-precinct-layer"]["use"]
    assert "all four polygons differ" in lagging
    assert "lagging geometry" in lagging
    assert "tarrant-county-obsolete-2010-precinct-service" in manifest
    assert "2010" in manifest["tarrant-county-obsolete-2010-precinct-service"]["use"]
    assert "tarrant-county-stale-commissioner-map-page" in manifest
    stale_roster = manifest["tarrant-county-stale-commissioner-map-page"]["use"]
    assert "Roy C. Brooks" in stale_roster
    assert "Gary Fickes" in stale_roster
    assert "census-tarrant-county" in manifest

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:tarrant:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "tarrant-county-countywide"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["source_district_field"] == "District_N"
        assert str(attributes["District_N"]) == district_id
        found[district_id] = props["geometry_id"]
    assert found == {
        "1": "tarrant-county-commissioner-precinct-1",
        "2": "tarrant-county-commissioner-precinct-2",
        "3": "tarrant-county-commissioner-precinct-3",
        "4": "tarrant-county-commissioner-precinct-4",
    }
