from __future__ import annotations

import json

import pytest

import scripts.validate_tarrant_arcgis_metadata as metadata


class FakeResponse:
    def __init__(self, payload: dict | str) -> None:
        if isinstance(payload, dict):
            self.body = json.dumps(payload).encode("utf-8")
        else:
            self.body = payload.encode("utf-8")

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None


def controlling_payload() -> dict:
    return {
        "name": "Commissioner Precincts",
        "description": (
            "County Commissioner Precinct boundaries, effective beginning "
            "June 3rd 2025."
        ),
        "geometryType": "esriGeometryPolygon",
        "fields": [{"name": "District_N"}],
    }


def controlling_html() -> str:
    return """
    <html><body>
    <h2>Layer: Commissioner Precincts (ID: 3)</h2>
    Geometry Type: esriGeometryPolygon
    Description: County Commissioner Precinct boundaries, effective beginning June 3rd 2025.
    Fields: District_N
    Supported Query Formats: JSON, geoJSON, PBF
    </body></html>
    """


def test_metadata_contract_accepts_second_equivalent_format(monkeypatch) -> None:
    responses = iter([FakeResponse({}), FakeResponse(controlling_payload())])
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return next(responses)

    monkeypatch.setattr(metadata.urllib.request, "urlopen", fake_urlopen)

    payload = metadata.fetch_contract(
        "controlling",
        "https://example.test/MapServer/3",
        metadata.validate_controlling,
        attempts=1,
    )

    assert payload == controlling_payload()
    assert "f=pjson" in calls[0][0]
    assert "f=json" in calls[1][0]


def test_metadata_contract_accepts_official_html_representation(monkeypatch) -> None:
    responses = iter(
        [FakeResponse({}), FakeResponse({}), FakeResponse(controlling_html())]
    )
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        return next(responses)

    monkeypatch.setattr(metadata.urllib.request, "urlopen", fake_urlopen)

    payload = metadata.fetch_contract(
        "controlling",
        "https://example.test/MapServer/3",
        metadata.validate_controlling,
        html_validator=metadata.validate_controlling_html,
        attempts=1,
    )

    assert payload["validated_via"] == "html"
    assert "f=pjson" in calls[0]
    assert "f=json" in calls[1]
    assert "_cc_html_attempt=1" in calls[2]


def test_metadata_contract_retries_incomplete_successful_responses(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse({}),
            FakeResponse({}),
            FakeResponse(controlling_payload()),
        ]
    )
    sleeps = []
    monkeypatch.setattr(
        metadata.urllib.request,
        "urlopen",
        lambda _request, timeout: next(responses),
    )
    monkeypatch.setattr(metadata.time, "sleep", sleeps.append)

    payload = metadata.fetch_contract(
        "controlling",
        "https://example.test/MapServer/3",
        metadata.validate_controlling,
        attempts=2,
    )

    assert payload == controlling_payload()
    assert sleeps == [5]


def test_metadata_contract_fails_closed_after_bounded_attempts(monkeypatch) -> None:
    monkeypatch.setattr(
        metadata.urllib.request,
        "urlopen",
        lambda _request, timeout: FakeResponse({}),
    )
    monkeypatch.setattr(metadata.time, "sleep", lambda _seconds: None)

    with pytest.raises(SystemExit, match="failed after 2 attempts"):
        metadata.fetch_contract(
            "controlling",
            "https://example.test/MapServer/3",
            metadata.validate_controlling,
            attempts=2,
        )
