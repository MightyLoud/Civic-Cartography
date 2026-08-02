import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/fort-bend-county/current-commissioners-court.csv"
CONSTITUTIONAL = ROOT / "data/raw/fort-bend-county/current-countywide-constitutional-offices.csv"
MANIFEST = ROOT / "data/raw/fort-bend-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/fort_bend_county_commissioners_court.csv"
PRECINCTS = ROOT / "data/geojson/fort_bend_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/fort_bend_county_countywide.geojson"


def test_fort_bend_county_roster_succession_and_2026_geometry_contract() -> None:
    expected_court = {
        "County Judge": "Daniel Wong",
        "County Commissioner Precinct 1": "Vincent Morales Jr.",
        "County Commissioner Precinct 2": "Grady Prestage",
        "County Commissioner Precinct 3": "W. A. “Andy” Meyers",
        "County Commissioner Precinct 4": "Dexter L. McCoy",
    }
    expected_constitutional = {
        "Sheriff": "Eric Fagan",
        "County Clerk": "Laura Richard",
        "District Clerk": "Beverley McGrew Walker",
        "Tax Assessor-Collector": "Carmen P. Turner",
        "County Treasurer": "Bill Rickert",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected_court
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}

    with CONSTITUTIONAL.open(newline="", encoding="utf-8") as handle:
        constitutional = list(csv.DictReader(handle))
    assert len(constitutional) == 5
    assert {row["office_name"]: row["officeholder"] for row in constitutional} == expected_constitutional
    assert {row["geography_type"] for row in constitutional} == {"countywide"}
    assert {row["geography_id"] for row in constitutional} == {"COUNTYWIDE"}
    assert all("separately elected" in row["notes"] for row in constitutional)

    all_evidence = evidence + constitutional
    assert len(all_evidence) == 10
    assert len({row["officeholder"] for row in all_evidence}) == 10
    judge = next(row for row in evidence if row["office_name"] == "County Judge")
    assert "interim" in judge["notes"].lower()
    assert "April 13, 2026" in judge["notes"]
    assert "December 31, 2026" in judge["notes"]
    assert "KP George" not in " ".join(row["officeholder"] for row in all_evidence)
    elected_current_holders = [
        row for row in evidence if row["office_name"].startswith("County Commissioner")
    ] + constitutional
    assert len(elected_current_holders) == 9

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_type"] == "countywide")
    assert countywide["office_name"] == (
        "County Judge + Sheriff + County Clerk + District Clerk + "
        "Tax Assessor-Collector + County Treasurer"
    )
    assert "interim-appointed" in countywide["notes"]
    for officeholder in expected_constitutional.values():
        assert officeholder in countywide["notes"]
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["geometry_source_url"] for row in commissioner_rows} == {
        "https://gisportal.fortbendcountytx.gov/arcgis/rest/services/InteractiveMap/Boundaries_Public/FeatureServer/7"
    }
    assert all("January 1, 2026" in row["notes"] for row in commissioner_rows)
    assert all("archived 2022-2025 geometry differs" in row["notes"] for row in commissioner_rows)

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 23
    assert "fort-bend-county-home-interim" in manifest
    assert "Interim County Judge" in manifest["fort-bend-county-home-interim"]["use"]
    assert "fort-bend-county-judge-interim-term" in manifest
    interim_term = manifest["fort-bend-county-judge-interim-term"]["use"]
    assert "April 13, 2026" in interim_term
    assert "December 31, 2026" in interim_term
    assert "fort-bend-county-stale-kp-george-bio" in manifest
    predecessor = manifest["fort-bend-county-stale-kp-george-bio"]["use"]
    assert "KP George" in predecessor
    assert "stale predecessor" in predecessor
    directory = manifest["fort-bend-county-elected-officials"]["use"]
    expected_directory_names = {
        "Daniel Wong",
        "Vincent Morales",
        "Grady Prestage",
        "Andy Meyers",
        "Dexter L. McCoy",
        "Eric Fagan",
        "Laura Richard",
        "Beverley McGrew Walker",
        "Carmen Turner",
        "Bill Rickert",
    }
    assert all(name in directory for name in expected_directory_names)
    expected_new_sources = {
        "fort-bend-county-sheriff",
        "fort-bend-county-sheriff-history",
        "fort-bend-county-clerk",
        "fort-bend-county-district-clerk",
        "fort-bend-county-district-clerk-biography",
        "fort-bend-county-tax-assessor",
        "fort-bend-county-tax-rate-portal",
        "fort-bend-county-treasurer",
        "fort-bend-county-treasurer-history",
        "fort-bend-county-bail-bond-board",
    }
    assert expected_new_sources.issubset(manifest)
    assert "2021 to present" in manifest["fort-bend-county-sheriff-history"]["use"]
    assert "second term" in manifest["fort-bend-county-district-clerk-biography"]["use"]
    assert "Carmen Turner" in manifest["fort-bend-county-tax-rate-portal"]["use"]
    assert "2019 to present" in manifest["fort-bend-county-treasurer-history"]["use"]
    board = manifest["fort-bend-county-bail-bond-board"]["use"]
    assert "Bill Rickert" in board and "Laura Richard" in board
    current_layer = manifest["fort-bend-county-current-precinct-layer"]["use"]
    for field in ("NAME", "COMMISSION", "WEBSITE", "EFFECTIVE"):
        assert field in current_layer
    archive = manifest["fort-bend-county-archive-2022-2025"]["use"]
    assert "PRECINCT" in archive
    assert "All four archived polygons differ" in archive
    assert "census-fort-bend-county" in manifest

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:fort-bend:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "fort-bend-county-countywide"

    expected_commission = {
        "1": "Vincent Morales, Jr.",
        "2": "Grady Prestage",
        "3": "Andy Meyers",
        "4": "Dexter McCoy",
    }
    expected_website = {
        district_id: f"https://fortbendcountytx.gov/government/departments/commissioners-court/commissioner-precinct-{district_id}"
        for district_id in ("1", "2", "3", "4")
    }
    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["source_district_field"] == "NAME"
        assert str(attributes["NAME"]) == district_id
        assert attributes["COMMISSION"] == expected_commission[district_id]
        assert attributes["WEBSITE"] == expected_website[district_id]
        assert attributes["EFFECTIVE"] == 1767225600000
        found[district_id] = props["geometry_id"]
    assert found == {
        "1": "fort-bend-county-commissioner-precinct-1",
        "2": "fort-bend-county-commissioner-precinct-2",
        "3": "fort-bend-county-commissioner-precinct-3",
        "4": "fort-bend-county-commissioner-precinct-4",
    }
