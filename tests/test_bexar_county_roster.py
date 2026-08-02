import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/bexar-county/current-commissioners-court.csv"
COUNTYWIDE_EVIDENCE = (
    ROOT / "data/raw/bexar-county/current-countywide-constitutional-offices.csv"
)
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
    assert len(manifest) == 18
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


def test_bexar_countywide_roles_share_one_geometry() -> None:
    expected = {
        "Sheriff": "Javier Salazar",
        "County Clerk": "Lucy Adame-Clark",
        "District Clerk": "Gloria A. Martinez",
        "Tax Assessor-Collector": "Albert Uresti",
        "County Treasurer Duties": "Lucy Adame-Clark",
    }

    with COUNTYWIDE_EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE"}
    assert {row["geography_type"] for row in evidence} == {"countywide"}
    assert len({row["officeholder"] for row in evidence}) == 4

    treasurer = next(row for row in evidence if row["office_name"] == "County Treasurer Duties")
    assert treasurer["officeholder"] == "Lucy Adame-Clark"
    assert "abolished" in treasurer["notes"]
    assert "November 6, 1984" in treasurer["notes"]
    assert "not a separately elected position" in treasurer["notes"]

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5

    countywide = [row for row in normalized if row["district_type"] == "countywide"]
    assert len(countywide) == 1
    row = countywide[0]
    assert row["record_id"] == "TX:county:bexar:countywide:COUNTYWIDE"
    assert row["geometry_id"] == "bexar-county-countywide"
    assert row["qa_status"] == "approved"
    assert row["parity_ok"] == "TRUE"
    for office in [
        "County Judge",
        "Sheriff",
        "County Clerk",
        "District Clerk",
        "Tax Assessor-Collector",
        "County Treasurer Duties",
    ]:
        assert office in row["office_name"]
    assert "abolished the separate Treasurer office in 1984" in row["notes"]
    assert "does not create a second countywide normalized row" in row["notes"]

    precincts = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(precincts) == 4
    assert {row["district_id"] for row in precincts} == {"1", "2", "3", "4"}

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 18
    assert "bexar-county-administrators" in manifest
    assert "bexar-county-sheriff" in manifest
    assert "bexar-county-clerk" in manifest
    assert "bexar-county-district-clerk" in manifest
    assert "bexar-county-tax-assessor-collector" in manifest
    assert "texas-bexar-treasurer-abolition" in manifest
    abolition = manifest["texas-bexar-treasurer-abolition"]["use"]
    assert "November 6, 1984" in abolition
    assert "abolishing the office of county treasurer" in abolition
    assert "bexar-county-elected-officials" in manifest
    assert "omits a separately elected County Treasurer" in manifest[
        "bexar-county-elected-officials"
    ]["use"]
