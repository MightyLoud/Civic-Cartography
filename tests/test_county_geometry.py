from scripts import fetch_arcgis_districts, fetch_tigerweb_county


POLYGON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
}


def test_county_canonicalize_uses_countywide_semantics():
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"GEOID": "48121", "NAME": "Denton County"},
                "geometry": POLYGON,
            }
        ],
    }

    canonical = fetch_tigerweb_county.canonicalize(
        raw,
        record_id="TX:county:denton:countywide:COUNTYWIDE",
        geometry_id="denton-county-countywide",
        retrieved_at="2026-08-01",
        request_url="https://example.test/query",
    )

    properties = canonical["features"][0]["properties"]
    assert properties["jurisdiction_name"] == "Denton County"
    assert properties["district_type"] == "countywide"
    assert properties["district_id"] == "COUNTYWIDE"
    assert properties["census_geoid"] == "48121"


def test_arcgis_inference_prefers_precinct_field():
    features = [
        {
            "type": "Feature",
            "properties": {"ID": number, "PRECINCT": f"Precinct {number}"},
            "geometry": POLYGON,
        }
        for number in range(1, 5)
    ]

    assert (
        fetch_arcgis_districts.infer_district_field(
            features, {"1", "2", "3", "4"}
        )
        == "PRECINCT"
    )


def test_arcgis_canonicalize_supports_commissioner_precincts():
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"PRECINCT": "Precinct 2"},
                "geometry": POLYGON,
            }
        ],
    }

    canonical = fetch_arcgis_districts.canonicalize(
        raw,
        district_field="PRECINCT",
        jurisdiction_name="Denton County",
        record_id_prefix="TX:county:denton:commissioner_precinct",
        geometry_id_prefix="denton-county-commissioner-precinct",
        source_agency="Denton County GIS",
        layer_url="https://example.test/MapServer/4",
        request_url="https://example.test/MapServer/4/query",
        retrieved_at="2026-08-01",
        district_type="commissioner_precinct",
        district_name_prefix="Commissioner Precinct",
    )

    properties = canonical["features"][0]["properties"]
    assert properties["record_id"] == "TX:county:denton:commissioner_precinct:2"
    assert properties["geometry_id"] == "denton-county-commissioner-precinct-2"
    assert properties["district_type"] == "commissioner_precinct"
    assert properties["district_name"] == "Commissioner Precinct 2"
