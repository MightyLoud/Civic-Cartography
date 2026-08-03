from __future__ import annotations

import csv
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from capture_upstream_batch import BatchCaptureError, _normalize_local_csv
from capture_upstream_fixtures import _install_fixed_datetime


def _rows(value: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(value.decode("utf-8"))))


def test_local_csv_normalization_skips_header_and_keeps_quoted_name() -> None:
    raw = (
        "id,name,extra,one,two,three\n"
        'ocd-division/country:us/state:nm/place:test,"Test, New Mexico",extra,1,2,3\n'
        "ocd-division/country:us/state:nm/county:test,Test County,other\n"
    ).encode()

    normalized = _normalize_local_csv(raw)

    assert _rows(normalized) == [
        ["ocd-division/country:us/state:nm/place:test", "Test, New Mexico"],
        ["ocd-division/country:us/state:nm/county:test", "Test County"],
    ]


def test_local_csv_normalization_rejects_short_rows() -> None:
    with pytest.raises(BatchCaptureError, match="fewer than two columns"):
        _normalize_local_csv(b"only-one-column\n")


def test_local_csv_normalization_rejects_unrecognized_identifier() -> None:
    with pytest.raises(BatchCaptureError, match="invalid OCD ID"):
        _normalize_local_csv(b"not-an-ocdid,Example\n")


def test_fixed_capture_clock_covers_recursive_ancestor_stubs() -> None:
    fixed_asof = datetime(2026, 8, 3, 18, 0, tzinfo=timezone.utc)
    leaf_division = SimpleNamespace()
    leaf_jurisdiction = SimpleNamespace()
    recursive_stubs = SimpleNamespace()

    _install_fixed_datetime(
        fixed_asof,
        leaf_division,
        leaf_jurisdiction,
        recursive_stubs,
    )

    for module in (leaf_division, leaf_jurisdiction, recursive_stubs):
        assert module.datetime.now(timezone.utc) == fixed_asof
        assert module.datetime.now() == fixed_asof.replace(tzinfo=None)
