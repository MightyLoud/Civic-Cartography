import json
import copy
from pathlib import Path

import pytest

from scripts.compare_tigerweb_snapshot import (
    compare_canonical_files,
    compare_raw_and_canonical,
    stable_source_view,
)


def raw_payload(*, object_id: int = 1, x: float = -98.49) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": object_id,
                "properties": {
                    "GEOID": "4853988",
                    "NAME": "Olmos Park city",
                    "OBJECTID": object_id,
                    "OID": str(object_id),
                    "DISP_CLR": 3,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[x, 29.47], [-98.48, 29.47], [x, 29.47]]],
                },
            }
        ],
    }


def canonical_payload(*, object_id: int = 1, x: float = -98.49) -> dict:
    payload = raw_payload(object_id=object_id, x=x)
    feature = payload["features"][0]
    feature.pop("id")
    source_attributes = feature["properties"]
    feature["properties"] = {
        "geometry_id": "olmos-park-citywide",
        "record_id": "TX:municipality:olmos-park:at_large:CITYWIDE",
        "source_attributes": source_attributes,
    }
    return payload


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_raw_and_canonical_service_ids_are_ignored(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    canonical = tmp_path / "canonical.json"
    write(raw, raw_payload(object_id=1))
    write(canonical, canonical_payload(object_id=999))

    assert compare_raw_and_canonical(raw, canonical) == []


def test_response_metadata_is_ignored(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    canonical = tmp_path / "canonical.json"
    raw_data = raw_payload()
    raw_data["exceededTransferLimit"] = False
    raw_data["metadata"] = {"requestId": "volatile"}
    raw_data["features"][0]["service_metadata"] = {"cache": "miss"}
    write(raw, raw_data)
    write(canonical, canonical_payload())

    assert compare_raw_and_canonical(raw, canonical) == []


def test_raw_geometry_change_is_reported(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    canonical = tmp_path / "canonical.json"
    write(raw, raw_payload(x=-98.49))
    write(canonical, canonical_payload(x=-98.50))

    errors = compare_raw_and_canonical(raw, canonical)

    assert any("disagree" in error for error in errors)


def test_canonical_service_ids_are_ignored(tmp_path: Path) -> None:
    committed = tmp_path / "committed.json"
    fresh = tmp_path / "fresh.json"
    write(committed, canonical_payload(object_id=1))
    write(fresh, canonical_payload(object_id=999))

    assert compare_canonical_files(committed, fresh) == []


def test_canonical_geometry_change_is_reported(tmp_path: Path) -> None:
    committed = tmp_path / "committed.json"
    fresh = tmp_path / "fresh.json"
    write(committed, canonical_payload(x=-98.49))
    write(fresh, canonical_payload(x=-98.50))

    errors = compare_canonical_files(committed, fresh)

    assert any("snapshot changed" in error for error in errors)


def test_canonical_join_change_is_reported(tmp_path: Path) -> None:
    committed = tmp_path / "committed.json"
    fresh = tmp_path / "fresh.json"
    committed_payload = canonical_payload()
    fresh_payload = canonical_payload()
    fresh_payload["features"][0]["properties"]["geometry_id"] = "wrong"
    write(committed, committed_payload)
    write(fresh, fresh_payload)

    errors = compare_canonical_files(committed, fresh)

    assert any("snapshot changed" in error for error in errors)


@pytest.mark.parametrize("field", ["AREALAND", "AREAWATER"])
def test_integer_area_representation_is_equivalent_without_mutating_input(field: str) -> None:
    raw = raw_payload()
    canonical = canonical_payload()
    raw["features"][0]["properties"][field] = "2709073"
    canonical["features"][0]["properties"]["source_attributes"][field] = 2709073
    original = copy.deepcopy(raw)
    assert stable_source_view(raw, canonical=False) == stable_source_view(canonical, canonical=True)
    assert raw == original


@pytest.mark.parametrize("fresh_value", [2709074, "2709074", "2709073.0", None])
def test_area_value_changes_still_fail(tmp_path: Path, fresh_value) -> None:
    committed = canonical_payload()
    fresh = canonical_payload()
    committed["features"][0]["properties"]["source_attributes"]["AREAWATER"] = "2709073"
    fresh["features"][0]["properties"]["source_attributes"]["AREAWATER"] = fresh_value
    write(tmp_path / "committed.json", committed)
    write(tmp_path / "fresh.json", fresh)
    errors = compare_canonical_files(tmp_path / "committed.json", tmp_path / "fresh.json")
    assert len(errors) == 1
    assert "source attributes changed: AREAWATER" in errors[0]


@pytest.mark.parametrize("field", ["GEOID", "NAME"])
def test_other_source_attributes_remain_strict(tmp_path: Path, field: str) -> None:
    committed = canonical_payload()
    fresh = canonical_payload()
    fresh["features"][0]["properties"]["source_attributes"][field] = 4853988
    write(tmp_path / "committed.json", committed)
    write(tmp_path / "fresh.json", fresh)
    assert compare_canonical_files(tmp_path / "committed.json", tmp_path / "fresh.json")


def test_geometry_and_provenance_drift_are_reported_separately(tmp_path: Path) -> None:
    committed = canonical_payload()
    fresh = canonical_payload(x=-98.50)
    committed["features"][0]["properties"]["source_vintage"] = "2025-01-01"
    fresh["features"][0]["properties"]["source_vintage"] = "2026-01-01"
    write(tmp_path / "committed.json", committed)
    write(tmp_path / "fresh.json", fresh)
    errors = compare_canonical_files(tmp_path / "committed.json", tmp_path / "fresh.json")
    assert "geometry changed" in errors[0]
    assert "canonical properties changed: source_vintage" in errors[0]
