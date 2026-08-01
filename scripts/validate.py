#!/usr/bin/env python3
"""Validate normalized civic CSV files before map publication."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

REQUIRED_COLUMNS = (
    "record_id",
    "state_fips",
    "state_abbr",
    "jurisdiction_type",
    "jurisdiction_name",
    "district_type",
    "district_id",
    "district_name",
    "source_url",
    "source_retrieved_at",
    "source_confidence",
    "qa_status",
    "parity_ok",
)

ALLOWED_JURISDICTION_TYPES = {
    "state",
    "county",
    "municipality",
    "school_district",
    "special_district",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_QA_STATUS = {"pending", "reviewed", "approved"}


def _value(row: dict[str, str | None], column: str) -> str:
    return (row.get(column) or "").strip()


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def validate_file(path: Path, seen_record_ids: set[str] | None = None) -> list[str]:
    """Return human-readable validation errors for one normalized CSV."""
    errors: list[str] = []
    seen = seen_record_ids if seen_record_ids is not None else set()

    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        return [f"{path}: unable to read file: {exc}"]

    with handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing_columns:
            return [f"{path}: missing required columns: {', '.join(missing_columns)}"]

        for line_number, row in enumerate(reader, start=2):
            prefix = f"{path}:{line_number}"

            for column in REQUIRED_COLUMNS:
                if not _value(row, column):
                    errors.append(f"{prefix}: blank required field '{column}'")

            record_id = _value(row, "record_id")
            if record_id:
                if record_id in seen:
                    errors.append(f"{prefix}: duplicate record_id '{record_id}'")
                else:
                    seen.add(record_id)

            state_fips = _value(row, "state_fips")
            if state_fips and not re.fullmatch(r"\d{2}", state_fips):
                errors.append(f"{prefix}: state_fips must be exactly two digits")

            state_abbr = _value(row, "state_abbr")
            if state_abbr and not re.fullmatch(r"[A-Z]{2}", state_abbr):
                errors.append(f"{prefix}: state_abbr must be two uppercase letters")

            jurisdiction_type = _value(row, "jurisdiction_type")
            if jurisdiction_type and jurisdiction_type not in ALLOWED_JURISDICTION_TYPES:
                errors.append(
                    f"{prefix}: unsupported jurisdiction_type '{jurisdiction_type}'"
                )

            source_url = _value(row, "source_url")
            if source_url and not source_url.lower().startswith(("http://", "https://")):
                errors.append(f"{prefix}: source_url must use http:// or https://")

            retrieved_at = _value(row, "source_retrieved_at")
            if retrieved_at and not _is_iso_date(retrieved_at):
                errors.append(
                    f"{prefix}: source_retrieved_at must be a valid YYYY-MM-DD date"
                )

            confidence = _value(row, "source_confidence").lower()
            if confidence and confidence not in ALLOWED_CONFIDENCE:
                errors.append(
                    f"{prefix}: source_confidence must be high, medium, or low"
                )

            qa_status = _value(row, "qa_status").lower()
            if qa_status and qa_status not in ALLOWED_QA_STATUS:
                errors.append(
                    f"{prefix}: qa_status must be pending, reviewed, or approved"
                )

            parity_ok = _value(row, "parity_ok").upper()
            if parity_ok and parity_ok != "TRUE":
                errors.append(f"{prefix}: parity_ok must be TRUE before publication")

    return errors


def validate_paths(paths: Iterable[Path]) -> list[str]:
    """Validate multiple files while enforcing cross-file record ID uniqueness."""
    errors: list[str] = []
    seen_record_ids: set[str] = set()
    for path in paths:
        errors.extend(validate_file(path, seen_record_ids))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="CSV files to validate; defaults to data/normalized/*.csv",
    )
    args = parser.parse_args()

    paths = args.paths or sorted(Path("data/normalized").glob("*.csv"))
    if not paths:
        print("No normalized CSV files found; scaffold check passed.")
        return 0

    errors = validate_paths(paths)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validation passed for {len(paths)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
