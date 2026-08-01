from __future__ import annotations

import io
import json
from unittest.mock import patch

import pytest

from scripts.fetch_tigerweb_school_district import canonicalize, fetch_school_district


SAMPLE_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "BASENAME": "Eanes Independent School District",
                "GEOID": "4817760",
                "OBJECTID": 42,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-97.9, 30.2], [-97.8, 30.2], [-97.9, 30.2]]],
            },
        }
    ],
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


def test_fetch_school_district_requires_one_matching_feature() -> None:
    response = FakeResponse(json.dumps(SAMPLE_PAYLOAD).encode("utf-8"))
    with patch("scripts.fetch_tigerweb_school_district.urlopen", return_value=response):
        payload, request_url = fetch_school_district("Eanes")

    assert payload == SAMPLE_PAYLOAD
    assert "BASENAME+LIKE" in request_url
    assert "%25Eanes%25" in request_url


def test_fetch_school_district_rejects_multiple_features() -> None:
    payload = {"type": "FeatureCollection", "features": SAMPLE_PAYLOAD["features"] * 2}
    response = FakeResponse(json.dumps(payload).encode("utf-8"))
    with patch("scripts.fetch_tigerweb_school_district.urlopen", return_value=response):
        with pytest.raises(ValueError, match="Expected one unified school district"):
            fetch_school_district("Eanes")


def test_canonicalize_adds_school_district_join_contract() -> None:
    result = canonicalize(
        SAMPLE_PAYLOAD,
        record_id="TX:school_district:eanes-isd:at_large:DISTRICTWIDE",
        geometry_id="eanes-isd-districtwide",
        retrieved_at="2026-08-01",
        request_url="https://example.test/query",
    )

    feature = result["features"][0]
    properties = feature["properties"]
    assert properties["record_id"] == (
        "TX:school_district:eanes-isd:at_large:DISTRICTWIDE"
    )
    assert properties["geometry_id"] == "eanes-isd-districtwide"
    assert properties["jurisdiction_type"] == "school_district"
    assert properties["district_type"] == "at_large"
    assert properties["district_id"] == "DISTRICTWIDE"
    assert properties["census_geoid"] == "4817760"
    assert feature["geometry"] == SAMPLE_PAYLOAD["features"][0]["geometry"]
