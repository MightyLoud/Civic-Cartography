from __future__ import annotations

import csv
import io

import pytest

from scripts.capture_upstream_batch import BatchCaptureError, _normalize_local_csv


def _rows(value: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(value.decode("utf-8"))))


def test_local_csv_normalization_keeps_id_and_quoted_name() -> None:
    raw = (
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
