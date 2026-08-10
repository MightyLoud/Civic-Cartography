from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import capture_upstream_batch as batch_capture
from capture_upstream_batch import (
    COUNTIES_GID,
    _combine_validation_csvs,
    _ensure_sources_for_states,
    _target_admin1_type,
    _target_uses_counties_validation,
)


def _rows(value: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(value.decode("utf-8"))))


def test_federal_district_root_uses_counties_validation() -> None:
    target = {
        "target_id": "MB100-075",
        "state": "dc",
        "selector": {
            "type": "ocdid",
            "value": "ocd-division/country:us/district:dc",
        },
    }

    assert _target_admin1_type(target) == "district"
    assert _target_uses_counties_validation(target, "district") is True


def test_federal_district_child_does_not_use_counties_validation() -> None:
    target = {
        "target_id": "DC-ANC",
        "state": "dc",
        "selector": {
            "type": "ocdid",
            "value": "ocd-division/country:us/district:dc/anc:1a",
        },
    }

    assert _target_admin1_type(target) == "district"
    assert _target_uses_counties_validation(target, "district") is False


def test_non_district_target_does_not_use_counties_validation() -> None:
    target = {
        "target_id": "CITY",
        "state": "wy",
        "selector": {
            "type": "ocdid",
            "value": "ocd-division/country:us/state:wy/place:cheyenne",
        },
    }

    assert _target_uses_counties_validation(target, "state") is False


def test_district_counties_source_is_retained_without_state_local_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloaded: list[str] = []

    def fake_download(url: str, path: Path) -> None:
        downloaded.append(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "GEOID_Census,NAMELSAD,STATEFP\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(batch_capture.base_capture, "_download_once", fake_download)
    api = {
        "master_url": "https://example.test/country-us.csv",
        "validation_url": (
            "https://docs.google.com/spreadsheets/d/example/"
            "export?format=csv&gid=1481694121"
        ),
        "local_url": lambda state: f"https://example.test/state-{state}-local.csv",
    }

    result = _ensure_sources_for_states(
        api,
        tmp_path,
        [],
        districts=["dc"],
        include_counties=True,
    )

    assert len(downloaded) == 3
    assert downloaded[-1].endswith(f"format=csv&gid={COUNTIES_GID}")
    assert not any("state-dc" in url for url in downloaded)
    assert result["manifest"]["districts"] == ["dc"]
    assert result["manifest"]["validation_strategy"] == {
        "municipalities_retained": True,
        "counties_retained": True,
        "territory_counties_retained": False,
        "strategy": (
            "combine compatible retained validation exports for the generator "
            "when a district root or territory county-equivalent target is present"
        ),
    }
    assert result["manifest"]["files"].keys() == {
        "counties_validation",
        "master",
        "validation",
    }
    stored = json.loads((tmp_path / "source-manifest.json").read_text())
    assert stored["files"]["counties_validation"]["path"] == (
        "nested-divisions-counties-validation.csv"
    )


def test_combined_validation_retains_dc_place_and_county_equivalent(
    tmp_path: Path,
) -> None:
    municipalities = tmp_path / "municipalities.csv"
    municipalities.write_text(
        "GEOID_Census,NAMELSAD,STATEFP\n"
        "1150000,Washington city,11\n",
        encoding="utf-8",
    )
    counties = tmp_path / "counties.csv"
    counties.write_text(
        "GEOID_Census,NAMELSAD,STATEFP\n"
        "11001,District of Columbia,11\n",
        encoding="utf-8",
    )

    output = _combine_validation_csvs(
        [municipalities, counties],
        tmp_path / "effective.csv",
    )

    assert _rows(output.read_bytes()) == [
        ["GEOID_Census", "NAMELSAD", "STATEFP"],
        ["1150000", "Washington city", "11"],
        ["11001", "District of Columbia", "11"],
    ]
