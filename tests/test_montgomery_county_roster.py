import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/montgomery-county/current-elected-offices.csv"
MANIFEST = ROOT / "data/raw/montgomery-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/montgomery_county_elected_offices.csv"
PRECINCTS = ROOT / "data/geojson/montgomery_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/montgomery_county_countywide.geojson"
LAYER = "https://services1.arcgis.com/PRoAPGnMSUqvTrzq/arcgis/rest/services/CountyDistrict_Commissioner/FeatureServer/0"


def test_montgomery_county_freshness_convergence_and_live_gis_roster() -> None:
    expected = {
        "County Judge": "Mark J. Keough",
        "County Commissioner Precinct 1": "Robert C. Walker",
        "County Commissioner Precinct 2": "Charlie Riley",
        "County Commissioner Precinct 3": "Ritch Wheeler",
        "County Commissioner Precinct 4": "Matt Gray",
        "Sheriff": "Wesley Doolittle",
        "County Clerk": "L. Brandon Steinmann",
        "District Clerk": "Melisa Miller",
        "Tax Assessor-Collector": "Tammy J. McRae",
        "County Treasurer": "Melanie Bush",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 10
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert len({row["officeholder"] for row in evidence}) == 10
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    current_holders = {row["officeholder"] for row in evidence}
    for excluded in ("James Noack", "James Metts", "Ryan Gable"):
        assert excluded not in current_holders
    assert "predecessor" in next(row["notes"] for row in evidence if row["geography_id"] == "3")
    assert "Constable Precinct 3" in next(row["notes"] for row in evidence if row["geography_id"] == "4")

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 18
    assert "February 18, 2026" in manifest["montgomery-elections-roster"]["use"]
    assert "April 24, 2026" in manifest["montgomery-commissioner-dataset"]["use"]
    assert "February 26, 2026" in manifest["montgomery-lookup-app"]["use"]
    assert "06f7b0e0e2354c8f8e77be19c4256ff5" in manifest["montgomery-lookup-app"]["url"]
    assert "8d0ca3edd9bb46f9aea60c99faa54e83" in manifest["montgomery-lookup-web-map"]["url"]
    assert "ea4f547b5eec474b8eb6d022afe173b3" in manifest["montgomery-commissioner-dataset"]["url"]
    assert manifest["montgomery-operational-layer"]["url"] == LAYER
    operational_use = manifest["montgomery-operational-layer"]["use"]
    for marker in ("DISTRICTID", "C1", "C4", "REPNAME1", "Ritch Wheeler", "Matt Gray"):
        assert marker in operational_use

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_id"] == "COUNTYWIDE")
    for office in (
        "County Judge", "Sheriff", "County Clerk", "District Clerk",
        "Tax Assessor-Collector", "County Treasurer",
    ):
        assert office in countywide["office_name"]
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["geometry_source_url"] for row in commissioner_rows} == {LAYER}
    assert all("DISTRICTID C" in row["notes"] for row in commissioner_rows)
    assert all("REPNAME1" in row["notes"] for row in commissioner_rows)

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:montgomery:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "montgomery-county-countywide"
    assert county_props["census_geoid"] == "48339"

    expected_gis_names = {
        "1": "Robert Walker",
        "2": "Charlie Riley",
        "3": "Ritch Wheeler",
        "4": "Matt Gray",
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
        assert props["source_layer"] == LAYER
        assert props["source_district_field"] == "DISTRICTID"
        assert str(attributes["DISTRICTID"]) == f"C{precinct_id}"
        assert str(attributes["NAME"]) == f"Commissioner Precinct {precinct_id}"
        assert str(attributes["REPNAME1"]) == expected_gis_names[precinct_id]
        found[precinct_id] = props["geometry_id"]
    assert found == {
        "1": "montgomery-county-commissioner-precinct-1",
        "2": "montgomery-county-commissioner-precinct-2",
        "3": "montgomery-county-commissioner-precinct-3",
        "4": "montgomery-county-commissioner-precinct-4",
    }
