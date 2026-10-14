import io
import json
from unittest.mock import patch

import pytest

from scripts import fetch_tigerweb_county, fetch_tigerweb_place, fetch_tigerweb_school_district
from scripts.tigerweb_source import fetch_source_vintage, fetch_with_vintage


@pytest.mark.parametrize("year", [2025, 2026])
def test_vintage_is_read_from_official_layer_metadata(year: int) -> None:
    metadata = {"description": f"Counties (or statistically equivalent entities); January 1, {year} vintage"}
    with patch("scripts.tigerweb_source.urlopen", return_value=io.BytesIO(json.dumps(metadata).encode())):
        assert fetch_source_vintage("https://example.test/MapServer/82") == f"{year}-01-01"


@pytest.mark.parametrize("metadata", [
    {"error": {"message": "unavailable"}}, {}, [],
    {"description": "Current counties"},
    {"description": "Counties; February 30, 2026 vintage"},
])
def test_missing_or_invalid_vintage_fails_closed(metadata) -> None:
    with patch("scripts.tigerweb_source.urlopen", return_value=io.BytesIO(json.dumps(metadata).encode())):
        with pytest.raises(ValueError):
            fetch_source_vintage("https://example.test/MapServer/82")


def test_vintage_rollover_during_fetch_is_rejected() -> None:
    with patch("scripts.tigerweb_source.fetch_source_vintage", side_effect=["2025-01-01", "2026-01-01"]):
        with pytest.raises(ValueError, match="changed during the fetch"):
            fetch_with_vintage("https://example.test/MapServer/82", lambda: ({}, "query"))


@pytest.mark.parametrize("module,selector,fetch_name", [
    (fetch_tigerweb_county, ["--geoid", "48121"], "fetch_county"),
    (fetch_tigerweb_place, ["--geoid", "4853988"], "fetch_place"),
    (fetch_tigerweb_school_district, ["--name-token", "Eanes"], "fetch_school_district"),
])
def test_cli_verifies_vintage_before_writing(module, selector, fetch_name, tmp_path) -> None:
    raw = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"GEOID": "48121", "NAME": "Denton County"},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]},
    }]}
    output = tmp_path / "canonical.json"
    raw_output = tmp_path / "raw.json"
    argv = ["fetch", *selector, "--record-id", "record", "--geometry-id", "geometry",
            "--retrieved-at", "2026-10-14", "--output", str(output), "--raw-output", str(raw_output)]
    with patch("sys.argv", argv), patch.object(module, fetch_name, return_value=(raw, "query")):
        with patch("scripts.tigerweb_source.fetch_source_vintage", return_value="2026-01-01"):
            assert module.main() == 0
        canonical = json.loads(output.read_text())
        assert canonical["features"][0]["properties"]["source_vintage"] == "2026-01-01"
        assert canonical["features"][0]["geometry"] == raw["features"][0]["geometry"]
        assert json.loads(raw_output.read_text()) == raw
        before = output.read_bytes(), raw_output.read_bytes()
        with patch("scripts.tigerweb_source.fetch_source_vintage", side_effect=["2025-01-01", "2026-01-01"]):
            with pytest.raises(ValueError, match="changed during the fetch"):
                module.main()
        assert (output.read_bytes(), raw_output.read_bytes()) == before
