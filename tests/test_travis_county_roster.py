import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/travis-county/current-commissioners-court.csv"
MANIFEST = ROOT / "data/raw/travis-county/source-manifest.csv"
RAW_PRECINCTS = ROOT / "data/raw/travis-county/commissioner-precincts-1-4.geojson"
NORMALIZED = ROOT / "data/normalized/travis_county_commissioners_court.csv"


def normalize_name(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def test_travis_county_roster_geometry_and_source_conflict() -> None:
    expected = {
        "COUNTYWIDE": "Andy Brown",
        "1": "Jeff Travillion",
        "2": "Brigid Shea",
        "3": "Ann Howard",
        "4": "George Morales",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 5
    assert {row["geography_id"]: row["officeholder"] for row in evidence} == expected

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["district_id"] for row in normalized} == set(expected)
    assert all(row["qa_status"] == "approved" for row in normalized)
    assert all(row["parity_ok"] == "TRUE" for row in normalized)

    payload = json.loads(RAW_PRECINCTS.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    assert len(features) == 4
    found = {
        str((feature.get("properties") or {}).get("PRECINCT")): normalize_name(
            (feature.get("properties") or {}).get("COMMISSIONER")
        )
        for feature in features
    }
    assert found == {
        precinct: normalize_name(name)
        for precinct, name in expected.items()
        if precinct != "COUNTYWIDE"
    }

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 11
    assert "travis-county-commissioner-precincts-current" in manifest
    assert "travis-county-commissioner-precincts-simple" in manifest
    assert "travis-county-financial-transparency-directory" in manifest
    stale_text = " ".join(row["use"] for row in manifest.values())
    assert "Margaret Gomez" in stale_text
    assert "George Morales" in stale_text
