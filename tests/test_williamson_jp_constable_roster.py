import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTABLES = ROOT / "data/raw/williamson-county/current-constables.csv"
JUSTICES = ROOT / "data/raw/williamson-county/current-justices-of-the-peace.csv"
NORMALIZED = ROOT / "data/normalized/williamson_county_commissioners_court.csv"
CANONICAL = ROOT / "data/geojson/williamson_county_commissioner_precincts.geojson"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_williamson_shared_commissioner_constable_jp_contract() -> None:
    expected_constables = {
        "1": "Mickey Chance",
        "2": "Jeff Anderson",
        "3": "Kevin Wilkie",
        "4": "Paul Leal",
    }
    expected_justices = {
        "1": "KT Musselman",
        "2": "Angela Williams",
        "3": "Evelyn McLean",
        "4": "Rhonda Redden",
    }

    constables = read_csv(CONSTABLES)
    justices = read_csv(JUSTICES)
    assert len(constables) == 4
    assert len(justices) == 4
    assert {row["geography_id"]: row["officeholder"] for row in constables} == expected_constables
    assert {row["geography_id"]: row["officeholder"] for row in justices} == expected_justices

    normalized = read_csv(NORMALIZED)
    precinct_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(normalized) == 5
    assert len(precinct_rows) == 4
    assert {row["district_id"] for row in precinct_rows} == {"1", "2", "3", "4"}
    for row in precinct_rows:
        assert "County Commissioner" in row["office_name"]
        assert "Constable" in row["office_name"]
        assert "Justice of the Peace" in row["office_name"]
        assert row["qa_status"] == "approved"
        assert row["parity_ok"] == "TRUE"

    payload = json.loads(CANONICAL.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    assert len(features) == 4
    labels: dict[str, str] = {}
    for feature in features:
        props = feature.get("properties") or {}
        precinct = str(props.get("district_id") or "")
        source_attributes = props.get("source_attributes") or {}
        labels[precinct] = str(source_attributes.get("LABEL_NAME") or "").strip().upper()
        assert str(source_attributes.get("COUNTY") or "").strip().upper() == "WILLIAMSON"
        assert props.get("source_district_field") == "LABEL_NAME"

    assert labels == {"1": "PCT 1", "2": "PCT 2", "3": "PCT 3", "4": "PCT 4"}
