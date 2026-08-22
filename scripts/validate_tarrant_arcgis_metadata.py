#!/usr/bin/env python3
"""Validate the Tarrant County ArcGIS source hierarchy with bounded retries."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from typing import Any, Callable
from urllib.parse import urlencode

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)
URLS = {
    "controlling": (
        "https://mapit.tarrantcounty.com/arcgis/rest/services/"
        "BondProject/BondProjects/MapServer/3"
    ),
    "general": (
        "https://mapit.tarrantcounty.com/arcgis/rest/services/"
        "Dynamic/CommissionerPrecinct/MapServer/0"
    ),
    "stale_2010": (
        "https://mapit.tarrantcounty.com/arcgis/rest/services/"
        "Dynamic/CommPct_Outline/MapServer"
    ),
}
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json,text/plain,*/*",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
HTML_HEADERS = {
    **HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
Validator = Callable[[dict[str, Any]], None]
HtmlValidator = Callable[[str], None]


def field_names(payload: dict[str, Any]) -> set[str]:
    return {
        str(field.get("name"))
        for field in payload.get("fields", [])
        if isinstance(field, dict) and field.get("name") is not None
    }


def validate_controlling(payload: dict[str, Any]) -> None:
    """Validate the exact controlling layer fingerprint.

    Some Tarrant ArcGIS responses to hosted runners omit only the free-text
    description. A blank description is controlled separately from a changed
    description: it is allowed only when every stable layer identifier remains
    exact, and the workflow subsequently requires exact geometry reproduction.
    """
    expected = {
        "id": 3,
        "name": "Commissioner Precincts",
        "type": "Feature Layer",
        "geometryType": "esriGeometryPolygon",
        "copyrightText": "Elections",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(
                f"unexpected controlling {key}: {payload.get(key)!r} != {value!r}"
            )
    if "District_N" not in field_names(payload):
        raise ValueError("controlling layer lost District_N")
    formats = str(payload.get("supportedQueryFormats") or "")
    if "geojson" not in formats.casefold():
        raise ValueError(f"controlling layer lost GeoJSON query support: {formats!r}")

    description = str(payload.get("description") or "").strip()
    if description:
        if "June 3rd 2025" not in description and "June 3, 2025" not in description:
            raise ValueError(
                f"controlling layer has a contradictory effective-date description: {description!r}"
            )
        print("Tarrant controlling effective-date description is present and exact.")
    else:
        print(
            "Tarrant controlling description was omitted by this ArcGIS response; "
            "the exact layer fingerprint matched and downstream exact geometry "
            "reproduction remains mandatory."
        )


def validate_general(payload: dict[str, Any]) -> None:
    if payload.get("geometryType") != "esriGeometryPolygon":
        raise ValueError(
            f"unexpected general geometry type: {payload.get('geometryType')!r}"
        )
    if "District_N" not in field_names(payload):
        raise ValueError("general layer lost District_N")


def validate_stale(payload: dict[str, Any]) -> None:
    text = " ".join(
        str(payload.get(key) or "")
        for key in ("serviceDescription", "description", "mapName")
    )
    if "2010" not in text:
        raise ValueError(f"explicit 2010 stale-service marker is missing: {text!r}")


def require_html_markers(text: str, markers: tuple[str, ...]) -> None:
    missing = [marker for marker in markers if marker.casefold() not in text.casefold()]
    if missing:
        raise ValueError(f"HTML metadata lost markers: {missing!r}")


def validate_controlling_html(text: str) -> None:
    require_html_markers(
        text,
        (
            "Layer: Commissioner Precincts",
            "Geometry Type: esriGeometryPolygon",
            "County Commissioner Precinct boundaries, effective beginning June 3rd 2025.",
            "District_N",
            "Supported Query Formats",
            "geoJSON",
        ),
    )


def validate_general_html(text: str) -> None:
    require_html_markers(
        text,
        ("Geometry Type: esriGeometryPolygon", "District_N", "Supported Query Formats"),
    )


def validate_stale_html(text: str) -> None:
    require_html_markers(text, ("2010", "Commissioner"))


def read_json(response: Any, *, request_url: str) -> dict[str, Any]:
    body = response.read()
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = " ".join(body[:240].decode("utf-8", errors="replace").split())
        raise ValueError(
            f"non-JSON metadata response from {request_url}; preview={preview!r}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"metadata response from {request_url} is not an object")
    if payload.get("error") is not None:
        raise ValueError(
            f"ArcGIS metadata error from {request_url}: {payload['error']!r}"
        )
    return payload


def read_html(response: Any, *, request_url: str) -> str:
    body = response.read()
    text = body.decode("utf-8", errors="replace")
    if not text.strip():
        raise ValueError(f"empty HTML metadata response from {request_url}")
    return text


def html_diagnostic(text: str) -> str:
    body = text.encode("utf-8")
    preview = " ".join(text[:500].split())[:200]
    return (
        f"bytes={len(body)} sha256={hashlib.sha256(body).hexdigest()} "
        f"preview={preview!r}"
    )


def fetch_contract(
    label: str,
    base_url: str,
    validator: Validator,
    *,
    html_validator: HtmlValidator | None = None,
    attempts: int = 5,
) -> dict[str, Any]:
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        for response_format in ("pjson", "json"):
            request_url = f"{base_url}?{urlencode({'f': response_format, '_cc_attempt': attempt})}"
            request = urllib.request.Request(request_url, headers=HEADERS)
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    payload = read_json(response, request_url=request_url)
                validator(payload)
                print(f"Validated Tarrant {label} metadata through ArcGIS {response_format}.")
                return payload
            except Exception as exc:
                errors.append(
                    f"attempt={attempt} format={response_format}: {exc}"
                )

        if html_validator is not None:
            request_url = f"{base_url}?{urlencode({'_cc_html_attempt': attempt})}"
            request = urllib.request.Request(request_url, headers=HTML_HEADERS)
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    text = read_html(response, request_url=request_url)
                html_validator(text)
                print(f"Validated Tarrant {label} metadata through ArcGIS HTML directory.")
                return {"validated_via": "html", "request_url": request_url}
            except Exception as exc:
                diagnostic = html_diagnostic(text) if "text" in locals() else "no_body"
                errors.append(
                    f"attempt={attempt} format=html: {exc}; {diagnostic}"
                )
            finally:
                if "text" in locals():
                    del text

        if attempt < attempts:
            time.sleep(attempt * 5)
    raise SystemExit(
        f"Tarrant {label} metadata contract failed after {attempts} attempts: "
        + " | ".join(errors[-6:])
    )


def main() -> int:
    fetch_contract(
        "controlling",
        URLS["controlling"],
        validate_controlling,
        html_validator=validate_controlling_html,
    )
    fetch_contract(
        "general",
        URLS["general"],
        validate_general,
        html_validator=validate_general_html,
    )
    fetch_contract(
        "stale_2010",
        URLS["stale_2010"],
        validate_stale,
        html_validator=validate_stale_html,
    )
    print("Tarrant County ArcGIS metadata hierarchy matches the release contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
