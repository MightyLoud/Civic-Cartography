import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/williamson-county/current-countywide-constitutional-offices.csv"
MANIFEST = ROOT / "data/raw/williamson-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/williamson_county_commissioners_court.csv"


def test_williamson_countywide_offices_share_one_geometry() -> None:
    expected = {
        "Sheriff": "Matthew Lindemann",
        "County Clerk": "Nancy E. Rister",
        "District Clerk": "Lisa David",
        "Tax Assessor-Collector": "Catherine Totty",
        "County Treasurer": "D. Scott Heselmeyer",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE"}
    assert {row["geography_type"] for row in evidence} == {"countywide"}

    tax_row = next(row for row in evidence if row["office_name"] == "Tax Assessor-Collector")
    tax_notes = tax_row["notes"]
    assert "Catherine Totty" in tax_notes
    assert "July 21, 2026" in tax_notes
    assert "Larry Gaddes" in tax_notes
    assert "stale-source" in tax_notes

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5

    countywide = [row for row in normalized if row["district_type"] == "countywide"]
    assert len(countywide) == 1
    row = countywide[0]
    assert row["record_id"] == "TX:county:williamson:countywide:COUNTYWIDE"
    assert row["geometry_id"] == "williamson-county-countywide"
    assert row["qa_status"] == "approved"
    assert row["parity_ok"] == "TRUE"
    for office in ["County Judge", *expected.keys()]:
        assert office in row["office_name"]

    precincts = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(precincts) == 4
    assert {row["district_id"] for row in precincts} == {"1", "2", "3", "4"}

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert "williamson-county-tax-assessor-resignation" in manifest
    assert "williamson-county-tax-assessor-appointment" in manifest
    assert "williamson-county-tax-assessor-collector" in manifest
    assert "williamson-county-constables" in manifest
    assert "williamson-county-justice-courts" in manifest
    assert {f"williamson-county-constable-{index}" for index in range(1, 5)} <= set(manifest)
    assert {f"williamson-county-jp-{index}" for index in range(1, 5)} <= set(manifest)
    assert len(manifest) == 26
