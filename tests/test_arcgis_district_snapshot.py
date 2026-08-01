from scripts.compare_arcgis_district_snapshot import (
    compare_canonical_snapshots,
    compare_raw_to_canonical,
)
from scripts.fetch_arcgis_districts import canonicalize, select_features


def source_feature(object_id: int, district_id: int, x: float) -> dict:
    return {
        "type": "Feature",
        "id": object_id,
        "properties": {
            "OBJECTID": object_id,
            "DISTRICTID": district_id,
            "LABEL": f"District {district_id}",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[x, 32.7], [x + 0.01, 32.7], [x, 32.7]]],
        },
    }


def raw_payload(object_offset: int = 0, geometry_shift: float = 0.0) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            source_feature(3 + object_offset, 3, -97.2 + geometry_shift),
            source_feature(4 + object_offset, 4, -97.3 + geometry_shift),
            source_feature(5 + object_offset, 5, -97.4 + geometry_shift),
        ],
    }


def canonical_payload(raw: dict) -> dict:
    selected = select_features(
        raw,
        district_field="DISTRICTID",
        expected_ids={"3", "4", "5"},
    )
    return canonicalize(
        selected,
        district_field="DISTRICTID",
        jurisdiction_name="Arlington",
        record_id_prefix="TX:municipality:arlington:district",
        geometry_id_prefix="arlington-district",
        source_agency="City of Arlington",
        layer_url="https://example.test/MapServer/0",
        request_url="https://example.test/MapServer/0/query",
        retrieved_at="2026-08-01",
    )


def test_raw_supports_canonical() -> None:
    raw = raw_payload()
    canonical = canonical_payload(raw)

    assert compare_raw_to_canonical(
        raw,
        canonical,
        raw_label="raw",
        canonical_label="canonical",
    ) == []


def test_volatile_object_ids_do_not_create_drift() -> None:
    committed = canonical_payload(raw_payload(object_offset=0))
    fresh = canonical_payload(raw_payload(object_offset=100))

    assert compare_canonical_snapshots(committed, fresh) == []


def test_geometry_change_is_reported() -> None:
    committed = canonical_payload(raw_payload())
    fresh = canonical_payload(raw_payload(geometry_shift=0.1))

    errors = compare_canonical_snapshots(committed, fresh)

    assert any("differs" in error for error in errors)


def test_join_change_is_reported() -> None:
    committed = canonical_payload(raw_payload())
    fresh = canonical_payload(raw_payload())
    fresh["features"][0]["properties"]["geometry_id"] = "wrong"

    errors = compare_canonical_snapshots(committed, fresh)

    assert any("differs" in error for error in errors)
