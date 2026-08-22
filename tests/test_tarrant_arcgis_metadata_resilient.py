from __future__ import annotations

import json

import pytest

import scripts.validate_tarrant_arcgis_metadata_resilient as metadata


class Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        self.body = body
        self.headers = Headers({"Content-Type": content_type})
        self.status = 200

    @classmethod
    def json(cls, payload: dict) -> "FakeResponse":
        return cls(json.dumps(payload).encode("utf-8"))

    @classmethod
    def html(cls, text: str) -> "FakeResponse":
        return cls(text.encode("utf-8"), "text/html; charset=utf-8")

    def read(self) -> bytes:
        return self.body

    def getcode(self) -> int:
        return self.status

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


def generic_shell() -> str:
    return (
        '<!DOCTYPE html><html><head id="Head1"><title>ArcGIS REST Services '
        'Directory</title></head><body><a href="/arcgis/rest/services">'
        "Services</a></body></html>"
    )


def test_valid_second_json_format_is_accepted(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse.json({}),
            FakeResponse.json(controlling_payload()),
        ]
    )
    monkeypatch.setattr(
        metadata.urllib.request,
        "urlopen",
        lambda _request, timeout: next(responses),
    )

    status = metadata.fetch_contract(
        "controlling",
        "https://example.test/MapServer/3",
        metadata.validate_controlling,
        metadata.validate_controlling_html,
        attempts=1,
        sleep=lambda _seconds: None,
    )

    assert status.status == "verified"
    assert status.authority_effect == "none"


def test_empty_json_and_generic_shell_are_unavailable_not_drift(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse.json({}),
            FakeResponse.json({"error": {"code": 500, "message": "gateway"}}),
            FakeResponse.html(generic_shell()),
        ]
    )
    monkeypatch.setattr(
        metadata.urllib.request,
        "urlopen",
        lambda _request, timeout: next(responses),
    )

    status = metadata.fetch_contract(
        "controlling",
        "https://example.test/MapServer/3",
        metadata.validate_controlling,
        metadata.validate_controlling_html,
        attempts=1,
        sleep=lambda _seconds: None,
    )

    assert status.status == "unavailable"
    assert status.authority_effect == "none"


def test_populated_contradictory_metadata_still_fails_closed(monkeypatch) -> None:
    changed = controlling_payload()
    changed["description"] = "Commissioner precinct layer with no effective date"
    responses = iter(
        [
            FakeResponse.json(changed),
            FakeResponse.json({}),
            FakeResponse.html(generic_shell()),
        ]
    )
    monkeypatch.setattr(
        metadata.urllib.request,
        "urlopen",
        lambda _request, timeout: next(responses),
    )

    with pytest.raises(SystemExit, match="populated drift"):
        metadata.fetch_contract(
            "controlling",
            "https://example.test/MapServer/3",
            metadata.validate_controlling,
            metadata.validate_controlling_html,
            attempts=1,
            sleep=lambda _seconds: None,
        )


def test_populated_html_with_missing_date_fails_closed(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse.json({}),
            FakeResponse.json({}),
            FakeResponse.html(
                "<html><body>Commissioner Precinct District_N "
                "esriGeometryPolygon</body></html>"
            ),
        ]
    )
    monkeypatch.setattr(
        metadata.urllib.request,
        "urlopen",
        lambda _request, timeout: next(responses),
    )

    with pytest.raises(SystemExit, match="populated drift"):
        metadata.fetch_contract(
            "controlling",
            "https://example.test/MapServer/3",
            metadata.validate_controlling,
            metadata.validate_controlling_html,
            attempts=1,
            sleep=lambda _seconds: None,
        )
