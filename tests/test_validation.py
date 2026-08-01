import csv
from pathlib import Path

from scripts.validate import REQUIRED_COLUMNS, validate_file, validate_paths


def _valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "record_id": "TX:municipality:austin:council:05",
        "state_fips": "48",
        "state_abbr": "TX",
        "jurisdiction_type": "municipality",
        "jurisdiction_name": "Austin",
        "district_type": "council",
        "district_id": "05",
        "district_name": "District 5",
        "source_url": "https://example.gov/source",
        "source_retrieved_at": "2026-08-01",
        "source_confidence": "high",
        "qa_status": "approved",
        "parity_ok": "TRUE",
    }
    row.update(overrides)
    return row


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames=REQUIRED_COLUMNS) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_valid_file_passes(tmp_path: Path) -> None:
    path = tmp_path / "valid.csv"
    _write_csv(path, [_valid_row()])

    assert validate_file(path) == []


def test_parity_must_be_true(tmp_path: Path) -> None:
    path = tmp_path / "parity-failed.csv"
    _write_csv(path, [_valid_row(parity_ok="FALSE")])

    errors = validate_file(path)

    assert any("parity_ok must be TRUE" in error for error in errors)


def test_missing_required_column_fails(tmp_path: Path) -> None:
    path = tmp_path / "missing-column.csv"
    fieldnames = tuple(column for column in REQUIRED_COLUMNS if column != "source_url")
    row = _valid_row()
    row.pop("source_url")
    _write_csv(path, [row], fieldnames=fieldnames)

    errors = validate_file(path)

    assert errors == [f"{path}: missing required columns: source_url"]


def test_record_ids_are_unique_across_files(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_csv(first, [_valid_row()])
    _write_csv(second, [_valid_row()])

    errors = validate_paths([first, second])

    assert any("duplicate record_id" in error for error in errors)
