from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from civic_cartography.target_manifest import ManifestError, load_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = PROJECT_ROOT / "schemas" / "target-manifest.schema.json"


def _manifest(selector_value: str, census_geoid: str) -> dict:
    return {
        "version": 1,
        "name": "geography-identity-test",
        "state": "or",
        "source_manifest": "evidence/test/source.json",
        "selection_crosswalk": "evidence/test/crosswalk.json",
        "targets": [
            {
                "target_id": "OR-PB00-001",
                "jurisdiction_name": "Test Geography",
                "state": "or",
                "census_geoid": census_geoid,
                "wave": "OR-PB00-A",
                "selector": {"type": "ocdid", "value": selector_value},
                "expected_archetype": "AR-001",
                "expected_classification": "government",
                "category": "production",
            }
        ],
    }


def _write(tmp_path: Path, raw: dict) -> Path:
    path = tmp_path / "manifest.yml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_place_production_geoid_remains_seven_digits(tmp_path: Path) -> None:
    raw = _manifest(
        "ocd-division/country:us/state:or/place:portland",
        "4159000",
    )
    manifest = load_manifest(_write(tmp_path, raw))
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(raw)

    assert manifest.targets[0].census_geoid == "4159000"


def test_county_production_geoid_accepts_five_digits(tmp_path: Path) -> None:
    raw = _manifest(
        "ocd-division/country:us/state:or/county:baker",
        "41001",
    )
    manifest = load_manifest(_write(tmp_path, raw))
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(raw)

    assert manifest.targets[0].census_geoid == "41001"


@pytest.mark.parametrize(
    ("selector_value", "census_geoid", "message"),
    [
        (
            "ocd-division/country:us/state:or/place:portland",
            "41001",
            "seven-digit Census place GEOID",
        ),
        (
            "ocd-division/country:us/state:or/county:baker",
            "4159000",
            "five-digit Census county GEOID",
        ),
    ],
)
def test_selector_geoid_type_mismatches_fail_closed(
    tmp_path: Path,
    selector_value: str,
    census_geoid: str,
    message: str,
) -> None:
    raw = _manifest(selector_value, census_geoid)
    with pytest.raises(ManifestError, match=message):
        load_manifest(_write(tmp_path, raw))

    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(raw))
    assert errors


def test_unsupported_production_geography_type_fails_closed(tmp_path: Path) -> None:
    raw = _manifest(
        "ocd-division/country:us/state:or/school_district:example",
        "41001",
    )
    with pytest.raises(ManifestError, match="place or county"):
        load_manifest(_write(tmp_path, raw))
