from __future__ import annotations

import json

import pytest

import scripts.fetch_tarrant_arcgis_districts_resilient as resilient


class FakeResponse:
    def __init__(self, payload: dict | bytes) -> None:
        self.body = (
            json.dumps(payload).encode("utf-8")
            if isinstance(payload, dict)
            else payload
        )

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None


def feature(object_id: int, district_id: str) -> dict:
    x = float(object_id)
    return {
        "type": "Feature",
        "id": object_id,
        "properties": {
            "OBJECTID": object_id,
            "District_N": district_id,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[x, 0.0], [x + 0.5, 0.0], [x + 0.5, 0.5], [x, 0.0]]
            ],
        },
    }


def test_canonical_fetch_remains_primary(monkeypatch) -> None:
    expected = ({"type": "FeatureCollection", "features": [feature(1, "1")]}, "u")
    monkeypatch.setattr(resilient.shared, "fetch_layer", lambda _url: expected)
    monkeypatch.setattr(
        resilient.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("fallback should not run"),
    )

    assert resilient.fetch_layer_resilient("https://example.test/MapServer/3") == expected


def test_object_id_fallback_uses_same_query_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        resilient.shared,
        "fetch_layer",
        lambda _url: (_ for _ in ()).throw(ValueError("HTML shell")),
    )
    responses = iter(
        [
            FakeResponse({"objectIds": [2, 1]}),
            FakeResponse(
                {
                    "type": "FeatureCollection",
                    "features": [feature(1, "1"), feature(2, "2")],
                }
            ),
        ]
    )
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.method, timeout))
        return next(responses)

    monkeypatch.setattr(resilient.urllib.request, "urlopen", fake_urlopen)

    payload, request_url = resilient.fetch_layer_resilient(
        "https://example.test/MapServer/3"
    )

    assert [item["id"] for item in payload["features"]] == [1, 2]
    assert all("/MapServer/3/query" in url for url, _method, _timeout in calls)
    assert "where=1%3D1" in request_url
    assert "f=geojson" in request_url


def test_object_id_fallback_supports_bounded_chunks(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse({"objectIds": [1, 2]}),
            FakeResponse(
                {"type": "FeatureCollection", "features": [feature(1, "1")]}
            ),
            FakeResponse(
                {"type": "FeatureCollection", "features": [feature(2, "2")]}
            ),
        ]
    )
    monkeypatch.setattr(
        resilient.urllib.request,
        "urlopen",
        lambda _request, timeout: next(responses),
    )

    payload, _request_url = resilient.fetch_by_object_ids(
        "https://example.test/MapServer/3",
        chunk_size=1,
    )

    assert [item["id"] for item in payload["features"]] == [1, 2]


def test_both_exact_transports_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        resilient.shared,
        "fetch_layer",
        lambda _url: (_ for _ in ()).throw(ValueError("canonical failed")),
    )
    monkeypatch.setattr(
        resilient.urllib.request,
        "urlopen",
        lambda _request, timeout: FakeResponse(b"<html>gateway shell</html>"),
    )

    with pytest.raises(ValueError, match="canonical and object-ID"):
        resilient.fetch_layer_resilient("https://example.test/MapServer/3")


def test_arcgis_error_envelope_is_not_accepted(monkeypatch) -> None:
    monkeypatch.setattr(
        resilient.urllib.request,
        "urlopen",
        lambda _request, timeout: FakeResponse(
            {"error": {"code": 500, "message": "temporary failure"}}
        ),
    )

    with pytest.raises(ValueError, match="both equivalent transports"):
        resilient.fetch_by_object_ids("https://example.test/MapServer/3")
