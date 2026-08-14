from __future__ import annotations

import json

import pytest

import scripts.fetch_arcgis_districts as arcgis


class FakeResponse:
    def __init__(self, body: bytes, content_type: str) -> None:
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None


def feature_collection() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"District_N": "1"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                },
            }
        ],
    }


def test_fetch_layer_falls_back_to_equivalent_post_after_non_json_get(
    monkeypatch,
) -> None:
    calls = []
    payload = feature_collection()

    def fake_urlopen(request, timeout):
        calls.append((request.get_method(), request.full_url, request.data, timeout))
        if request.get_method() == "GET":
            return FakeResponse(b"\n<!doctype html><title>temporary proxy page</title>", "text/html")
        return FakeResponse(json.dumps(payload).encode("utf-8"), "application/geo+json")

    monkeypatch.setattr(arcgis, "urlopen", fake_urlopen)

    actual, request_url = arcgis.fetch_layer("https://example.test/MapServer/3")

    assert actual == payload
    assert [call[0] for call in calls] == ["GET", "POST"]
    assert calls[1][1] == "https://example.test/MapServer/3/query"
    assert calls[1][2] is not None
    assert b"where=1%3D1" in calls[1][2]
    assert b"f=geojson" in calls[1][2]
    assert request_url.startswith("https://example.test/MapServer/3/query?")


def test_fetch_layer_does_not_post_after_valid_get(monkeypatch) -> None:
    calls = []
    payload = feature_collection()

    def fake_urlopen(request, timeout):
        calls.append(request.get_method())
        return FakeResponse(json.dumps(payload).encode("utf-8"), "application/geo+json")

    monkeypatch.setattr(arcgis, "urlopen", fake_urlopen)

    actual, _request_url = arcgis.fetch_layer("https://example.test/MapServer/3")

    assert actual == payload
    assert calls == ["GET"]


def test_fetch_layer_fails_closed_when_get_and_post_are_invalid(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse(b"<html>not json</html>", "text/html"),
            FakeResponse(
                json.dumps({"error": {"message": "query unavailable"}}).encode("utf-8"),
                "application/json",
            ),
        ]
    )
    monkeypatch.setattr(arcgis, "urlopen", lambda _request, timeout: next(responses))

    with pytest.raises(ValueError, match="both equivalent transports") as error:
        arcgis.fetch_layer("https://example.test/MapServer/3")

    message = str(error.value)
    assert "GET:" in message
    assert "POST:" in message
    assert "temporary" not in message
