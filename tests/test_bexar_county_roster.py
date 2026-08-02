import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/bexar-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/bexar-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/bexar_county_commissioners_court.csv"
PRECINCTS = ROOT / "data/geojson/bexar_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/bexar_county_countywide.geojson"


def test_bexar_county_roster_and_geometry_contract() -> None:
    expected = {
        "County Judge": "Peter Sakai",
        "County Commissioner Precinct 1": "Rebeca Clay-Flores",
        "County Commissioner Precinct 2": "Justin Rodriguez",
        "County Commissioner Precinct 3": "Grant Moody",
        "County Commissioner Precinct 4": "Tommy Calvert",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    precinct_four = next(row for row in evidence if row["geography_id"] == "4")
    assert "Tommy Calvert Jr." in precinct_four["notes"]
    assert "naming alias" in precinct_four["notes"]
    assert "stale-source" in precinct_four["notes"]

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 11
    assert "bexar-county-obsolete-finance-roster" in manifest
    stale = manifest["bexar-county-obsolete-finance-roster"]["use"]
    assert "Nelson W. Wolff" in stale
    assert "obsolete" in stale
    assert "bexar-county-commissioner-precincts" in manifest
    assert "Comm" in manifest["bexar-county-commissioner-precincts"]["use"]
    assert "ComName" in manifest["bexar-county-commissioner-precincts"]["use"]
    assert "census-bexar-county" in manifest

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:bexar:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "bexar-county-countywide"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    websites = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["source_district_field"] == "Comm"
        assert str(attributes["Comm"]) == district_id
        found[district_id] = attributes["ComName"]
        websites[district_id] = attributes["Website"]
    assert found == {
        "1": "Rebeca Clay-Flores",
        "2": "Justin Rodriguez",
        "3": "Grant Moody",
        "4": "Tommy Calvert Jr.",
    }
    assert websites == {
        "1": "https://www.bexar.org/commissionerpct1",
        "2": "https://www.bexar.org/commissionerpct2",
        "3": "https://www.bexar.org/commissionerpct3",
        "4": "https://www.bexar.org/commissionerpct4",
    }
