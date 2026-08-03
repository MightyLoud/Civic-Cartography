import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/galveston-county/current-elected-offices.csv"
ABOLISHED = ROOT / "data/raw/galveston-county/abolished-constitutional-offices.csv"
MANIFEST = ROOT / "data/raw/galveston-county/source-manifest.csv"
CONTRACT = ROOT / "data/raw/galveston-county/portal-source-contract.json"
NORMALIZED = ROOT / "data/normalized/galveston_county_elected_offices.csv"
PRECINCTS = ROOT / "data/geojson/galveston_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/galveston_county_countywide.geojson"
OPERATIONAL_LAYER = "https://services5.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Galveston_County_Commissioner_Precincts_2026/FeatureServer/0"


def test_galveston_county_effective_cutover_contract() -> None:
    expected = {
        "County Judge": "Mark A. Henry",
        "County Commissioner Precinct 1": "Darrell Apffel",
        "County Commissioner Precinct 2": "Joe Giusti",
        "County Commissioner Precinct 3": "Hank Dugie",
        "County Commissioner Precinct 4": "Dr. Robin Armstrong",
        "Sheriff": "Jimmy Fullen",
        "County Clerk": "Dwight D. Sullivan",
        "District Clerk": "John D. Kinard",
        "Tax Assessor-Collector": "Cheryl E. Johnson",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 9
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert len({row["officeholder"] for row in evidence}) == 9
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert "County Treasurer" not in {row["office_name"] for row in evidence}

    with ABOLISHED.open(newline="", encoding="utf-8") as handle:
        abolished = list(csv.DictReader(handle))
    assert len(abolished) == 1
    treasurer = abolished[0]
    assert treasurer["office_name"] == "County Treasurer"
    assert treasurer["status"] == "abolished"
    assert treasurer["effective_date"] == "2024-01-01"
    assert treasurer["current_officeholder"] == ""
    assert treasurer["vacancy_status"] == "not_applicable"
    assert "division of the County Clerk" in treasurer["current_function_destination"]
    assert "not a vacancy" in treasurer["notes"]

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 18
    assert "June 29, 2026" in manifest["galveston-2026-map-cutover"]["use"]
    assert "January 1, 2024" in manifest["hjr-134-effective-date"]["use"]
    assert "division of the County Clerk" in manifest["galveston-treasury-division"]["use"]
    assert "stale" in manifest["galveston-stale-treasurer-directory"]["source_type"]
    assert "does not establish a vacancy" in manifest["galveston-stale-treasurer-directory"]["use"]
    assert "e0b0fef416cd42ad991b8ae95d22bb59" in manifest["galveston-arcgis-experience"]["use"]

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["experience_item_id"] == "e0b0fef416cd42ad991b8ae95d22bb59"
    assert contract["experience_item_title"] == "Galveston Final2"
    assert contract["experience_item_owner"] == "sigler_n"
    assert contract["effective_date"] == "2026-06-29"
    assert contract["operational_layer_url"] == OPERATIONAL_LAYER
    assert contract["district_field"] == "Commission"
    assert contract["district_values"] == ["1", "2", "3", "4"]
    selected = contract["selected_candidate"]
    assert selected["layer_url"] == OPERATIONAL_LAYER
    assert selected["post_cutover"] is True
    assert selected["referenced_by_experience_graph"] is True
    rejected = contract["rejected_candidates"]
    assert len(rejected) >= 2
    assert any("pre-cutover" in row["rejection_reason"] for row in rejected)
    assert all(row.get("layer_url") != OPERATIONAL_LAYER for row in rejected)

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_type"] == "countywide")
    for office in ("County Judge", "Sheriff", "County Clerk", "District Clerk", "Tax Assessor-Collector"):
        assert office in countywide["office_name"]
    assert "County Treasurer" not in countywide["office_name"]
    assert "abolished effective January 1, 2024" in countywide["notes"]
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["geometry_source_url"] for row in commissioner_rows} == {OPERATIONAL_LAYER}
    assert all("June 29, 2026" in row["notes"] for row in commissioner_rows)

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:galveston:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "galveston-county-countywide"
    assert county_props["census_geoid"] == "48167"

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
        assert props["source_district_field"] == "Commission"
        assert "Commission" in attributes
        assert re.search(rf"(?<!\d){precinct_id}(?!\d)", str(attributes["Commission"]))
        found[precinct_id] = props["geometry_id"]
    assert found == {
        "1": "galveston-county-commissioner-precinct-1",
        "2": "galveston-county-commissioner-precinct-2",
        "3": "galveston-county-commissioner-precinct-3",
        "4": "galveston-county-commissioner-precinct-4",
    }
