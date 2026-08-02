import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_GEOMETRY = ROOT / "data/raw/denton-county/constable-precincts-1-6.geojson"
JP_EVIDENCE = ROOT / "data/raw/denton-county/current-justices-of-the-peace.csv"
NORMALIZED = ROOT / "data/normalized/denton_county_constables.csv"


def normalize_name(value: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def test_denton_jp_evidence_and_shared_geometry_contract() -> None:
    expected = {
        "1": "Alan Wheeler",
        "2": "James R. DePiazza",
        "3": "James Kerbow",
        "4": "Harris Hughey",
        "5": "Mike Oglesby",
        "6": "Blanca Oliver",
    }

    with JP_EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 6
    assert {row["geography_id"]: row["officeholder"] for row in evidence} == expected

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 6
    assert {row["district_id"] for row in normalized} == set(expected)
    for row in normalized:
        assert "Constable" in row["office_name"]
        assert "Justice of the Peace" in row["office_name"]
        assert row["qa_status"] == "approved"
        assert row["parity_ok"] == "TRUE"

    payload = json.loads(RAW_GEOMETRY.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    assert len(features) == 6

    found: dict[str, str] = {}
    for feature in features:
        properties = feature.get("properties") or {}
        precinct = str(properties.get("JP_C") or "")
        found[precinct] = normalize_name(properties.get("NAME_JP"))

    assert set(found) == set(expected)
    for precinct, officeholder in expected.items():
        actual = found[precinct]
        accepted = {normalize_name(officeholder)}
        if precinct == "2":
            accepted.add(normalize_name("James DePiazza"))
        assert actual in accepted
