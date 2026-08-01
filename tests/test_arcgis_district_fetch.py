from scripts.fetch_arcgis_districts import (
    canonicalize,
    infer_district_field,
    normalize_identifier,
    select_features,
)


def feature(object_id: int, district: str, x: float) -> dict:
    return {
        "type": "Feature",
        "id": object_id,
        "properties": {
            "OBJECTID": object_id,
            "COUNCIL_DISTRICT": district,
            "NAME": f"Council District {district}",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[x, 32.7], [x + 0.01, 32.7], [x, 32.7]]],
        },
    }


def payload() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            feature(1, "District 1", -97.1),
            feature(3, "District 3", -97.2),
            feature(4, "District 4", -97.3),
            feature(5, "District 5", -97.4),
            feature(8, "District 8", -97.5),
        ],
    }


def test_normalize_identifier_handles_common_values() -> None:
    assert normalize_identifier(3) == "3"
    assert normalize_identifier(4.0) == "4"
    assert normalize_identifier("District 5") == "5"
    assert normalize_identifier("3 - South") == "3"
    assert normalize_identifier("District 3 / Place 2") is None


def test_infer_district_field_ignores_object_id() -> None:
    district_field = infer_district_field(
        payload()["features"], {"3", "4", "5"}
    )

    assert district_field == "COUNCIL_DISTRICT"


def test_select_features_returns_requested_districts_in_order() -> None:
    selected = select_features(
        payload(),
        district_field="COUNCIL_DISTRICT",
        expected_ids={"3", "4", "5"},
    )

    assert [
        item["properties"]["COUNCIL_DISTRICT"] for item in selected["features"]
    ] == ["District 3", "District 4", "District 5"]


def test_canonicalize_creates_unique_join_ids() -> None:
    selected = select_features(
        payload(),
        district_field="COUNCIL_DISTRICT",
        expected_ids={"3", "4", "5"},
    )
    canonical = canonicalize(
        selected,
        district_field="COUNCIL_DISTRICT",
        jurisdiction_name="Arlington",
        record_id_prefix="TX:municipality:arlington:district",
        geometry_id_prefix="arlington-district",
        source_agency="City of Arlington",
        layer_url="https://example.test/MapServer/0",
        request_url="https://example.test/MapServer/0/query",
        retrieved_at="2026-08-01",
    )

    assert [
        item["properties"]["geometry_id"] for item in canonical["features"]
    ] == [
        "arlington-district-3",
        "arlington-district-4",
        "arlington-district-5",
    ]
    assert [
        item["properties"]["record_id"] for item in canonical["features"]
    ] == [
        "TX:municipality:arlington:district:3",
        "TX:municipality:arlington:district:4",
        "TX:municipality:arlington:district:5",
    ]
