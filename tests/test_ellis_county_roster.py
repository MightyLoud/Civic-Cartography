from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data/raw/ellis-county/current-elected-offices.csv"
COMBINED = ROOT / "data/raw/ellis-county/combined-prosecutor-structure.csv"
NORMALIZED = ROOT / "data/normalized/ellis_county_elected_offices.csv"
CONTRACT = ROOT / "data/raw/ellis-county/gis-source-contract.json"
COMMISSIONERS = ROOT / "data/geojson/ellis_county_commissioner_precincts.geojson"
COUNTYWIDE = ROOT / "data/geojson/ellis_county_countywide.geojson"
EXPECTED_DIGEST = "cbac5b521198324dc1fa4e7a94974a27a5c91a84db401803d7235c5f3f2ae343"
EXPECTED_HOLDERS = {
    "County Judge": "John Wray",
    "County Commissioner Precinct 1": "Randy Stinson",
    "County Commissioner Precinct 2": "Lane Grayson",
    "County Commissioner Precinct 3": "Louis Ponder",
    "County Commissioner Precinct 4": "Kyle Butler",
    "Sheriff": "Brad Norman",
    "County and District Attorney": "Lindy Beaty",
    "County Clerk": "Krystal Valdez",
    "District Clerk": "Melanie Reed",
    "Tax Assessor-Collector": "Richard Rozier",
    "County Treasurer": "Cheryl Chambers",
}
EXPECTED_GROUPS = {
    "1": [*[str(value) for value in range(1001, 1015)], "1060"],
    "2": [str(value) for value in range(1015, 1027)],
    "3": [*[str(value) for value in range(1027, 1040)], "1061"],
    "4": [str(value) for value in range(1040, 1060)],
}


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def release_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((COUNTYWIDE, COMMISSIONERS), key=lambda item: item.name):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_ellis_roster_is_bounded_and_current() -> None:
    rows = csv_rows(ROSTER)
    assert len(rows) == 11
    actual = {row["office_name"]: row["officeholder"] for row in rows}
    assert actual == EXPECTED_HOLDERS
    assert len(set(actual.values())) == 11
    methods = {row["office_name"]: row["selection_method"] for row in rows}
    assert methods["County Judge"] == "appointment"
    assert all(method == "election" for office, method in methods.items() if office != "County Judge")


def test_ellis_has_one_combined_prosecutor_and_no_split_rows() -> None:
    roster = csv_rows(ROSTER)
    names = [row["office_name"] for row in roster]
    assert names.count("County and District Attorney") == 1
    assert not {"County Attorney", "District Attorney", "Criminal District Attorney"} & set(names)
    combined = csv_rows(COMBINED)
    assert len(combined) == 1
    assert combined[0]["current_officeholder"] == "Lindy Beaty"
    assert combined[0]["component_offices"] == "County Attorney; District Attorney"
    assert combined[0]["separate_county_attorney_row"] == "FALSE"
    assert combined[0]["separate_district_attorney_row"] == "FALSE"
    assert combined[0]["criminal_district_attorney_row"] == "FALSE"


def test_ellis_normalized_geography_has_complete_parity() -> None:
    rows = csv_rows(NORMALIZED)
    assert len(rows) == 5
    assert {row["district_type"] for row in rows} == {"countywide", "commissioner_precinct"}
    assert [row["district_id"] for row in rows if row["district_type"] == "commissioner_precinct"] == ["1", "2", "3", "4"]
    assert all(row["qa_status"] == "approved" for row in rows)
    assert all(row["parity_ok"] == "TRUE" for row in rows)


def test_ellis_split_aware_geometry_contract_is_exact() -> None:
    contract = load_json(CONTRACT)
    assert contract["commissioner_precinct_count"] == 4
    assert contract["voting_precinct_count"] == 61
    assert contract["commissioner_source_voting_precinct_ids"] == EXPECTED_GROUPS
    assert contract["split_descendants"] == {
        "1060": {"district": "1", "parent": "1006"},
        "1061": {"district": "3", "parent": "1038"},
    }
    assert contract["split_accepted_at"] == "2025-04-15"
    assert contract["split_effective_at"] == "2026-01-01"
    assert contract["all_voting_precincts_assigned"] is True
    assert contract["interdistrict_overlap_area_degrees"] == 0
    assert contract["union_symmetric_difference_area_degrees"] == 0


def test_ellis_canonical_geometry_joins_are_exact() -> None:
    commissioner = load_json(COMMISSIONERS)
    countywide = load_json(COUNTYWIDE)
    assert len(commissioner["features"]) == 4
    assert len(countywide["features"]) == 1
    ids = {feature["properties"]["record_id"] for feature in commissioner["features"]}
    assert ids == {f"TX:county:ellis:commissioner_precinct:{number}" for number in range(1, 5)}
    assert countywide["features"][0]["properties"]["record_id"] == "TX:county:ellis:countywide:COUNTYWIDE"
    assert all(feature["geometry"]["type"] in {"Polygon", "MultiPolygon"} for feature in commissioner["features"] + countywide["features"])


def test_ellis_release_digest_is_pinned() -> None:
    assert release_digest() == EXPECTED_DIGEST
