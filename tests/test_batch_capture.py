from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import capture_upstream_batch as batch_capture
from capture_upstream_batch import (
    BatchCaptureError,
    _ensure_sources_for_states,
    _master_candidates,
    _normalize_local_csv,
    _target_admin1_type,
)
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


def test_territory_selector_routes_to_national_master() -> None:
    target = {
        "target_id": "MB100-050",
        "state": "pr",
        "selector": {
            "type": "ocdid",
            "value": "ocd-division/country:us/territory:pr/municipio:san_juan",
        },
    }

    assert _target_admin1_type(target) == "territory"


def test_mixed_admin1_aliases_are_rejected() -> None:
    target = {
        "target_id": "MIXED",
        "state": "pr",
        "selector": {
            "type": "alias_group",
            "members": [
                "ocd-division/country:us/territory:pr/municipio:san_juan",
                "ocd-division/country:us/state:pr/place:san_juan",
            ],
        },
    }

    with pytest.raises(BatchCaptureError, match="multiple admin-1 types"):
        _target_admin1_type(target)


def test_territory_sources_skip_nonexistent_state_local_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloaded: list[str] = []

    def fake_download(url: str, path: Path) -> None:
        downloaded.append(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"source={url}\n".encode())

    monkeypatch.setattr(batch_capture.base_capture, "_download_once", fake_download)
    api = {
        "master_url": "https://example.test/country-us.csv",
        "validation_url": "https://example.test/validation.csv",
        "local_url": lambda state: f"https://example.test/state-{state}-local.csv",
    }

    result = _ensure_sources_for_states(
        api,
        tmp_path,
        [],
        territories=["pr"],
    )

    assert downloaded == [api["master_url"], api["validation_url"]]
    assert not any("state-pr" in url for url in downloaded)
    assert result["manifest"]["states"] == []
    assert result["manifest"]["territories"] == ["pr"]
    stored = json.loads((tmp_path / "source-manifest.json").read_text())
    assert stored["files"].keys() == {"master", "validation"}


def test_exact_territory_candidate_is_loaded_from_national_master() -> None:
    class FakeParsed:
        @classmethod
        def parse_ocdid(cls, value: str) -> SimpleNamespace:
            return SimpleNamespace(raw_ocdid=value, territory="pr", municipio="san_juan")

    class FakeIngest:
        def __init__(self, *, uuid, ocdid, raw_record) -> None:
            self.uuid = uuid
            self.ocdid = ocdid
            self.raw_record = raw_record

    target_ocdid = "ocd-division/country:us/territory:pr/municipio:san_juan"
    master = (
        "id,name,census_geoid\n"
        f"{target_ocdid},San Juan Municipio,place-72127\n"
    ).encode()
    api = {
        "OCDIdParsed": FakeParsed,
        "OCDidIngestResp": FakeIngest,
    }

    candidates = _master_candidates(api, master, {target_ocdid})

    candidate = candidates[target_ocdid]
    assert candidate.source == "master"
    assert candidate.name == "San Juan Municipio"
    assert candidate.ingest.ocdid.territory == "pr"
    assert candidate.ingest.raw_record["census_geoid"] == "place-72127"
