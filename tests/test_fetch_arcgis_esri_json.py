from scripts.fetch_arcgis_districts import esri_json_to_geojson, esri_rings_to_geojson


def test_esri_polygon_rings_convert_with_hole() -> None:
    exterior = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]
    hole = [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]]

    geometry = esri_rings_to_geojson([exterior, hole])

    assert geometry["type"] == "Polygon"
    assert len(geometry["coordinates"]) == 2
    assert geometry["coordinates"][0][0] == [0.0, 0.0]
    assert geometry["coordinates"][1][0] == [2.0, 2.0]


def test_esri_json_features_convert_to_geojson() -> None:
    payload = {
        "features": [
            {
                "attributes": {"PRECINCT": 1, "COMMISSIONER": "Example"},
                "geometry": {
                    "rings": [
                        [[-98, 30], [-98, 31], [-97, 31], [-97, 30], [-98, 30]]
                    ]
                },
            }
        ]
    }

    converted = esri_json_to_geojson(payload)

    assert converted["type"] == "FeatureCollection"
    assert len(converted["features"]) == 1
    feature = converted["features"][0]
    assert feature["properties"] == {"PRECINCT": 1, "COMMISSIONER": "Example"}
    assert feature["geometry"]["type"] == "Polygon"
