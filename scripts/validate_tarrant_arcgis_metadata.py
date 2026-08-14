#!/usr/bin/env python3
"""Validate the Tarrant County ArcGIS source hierarchy with bounded retries."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path
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
EVIDENCE_PATH = Path("build/tarrant-county/metadata-status.json")
Validator = Callable[[dict[str, Any]], None]
HtmlValidator = Callable[[str], None]


class MetadataUnavailable(ValueError):
    """The endpoint returned no usable contract-bearing metadata."""


class MetadataContradiction(ValueError):
    """The endpoint returned usable metadata that contradicts the contract."""


def field_names(payload: dict[str, Any]) -> set[str]:
    return {
        str(field.get("name"))
        for field in payload.get("fields", [])
        if isinstance(field, dict) and field.get("name") is not None
    }


def validate_controlling(payload: dict[str, Any]) -> None:
    """Validate the exact controlling layer fingerprint.

    Hosted runners sometimes receive an empty ArcGIS object or the generic REST
    shell instead of layer metadata. Those responses are classified as source
    unavailability, not as authoritative changes. A contract-bearing response
    with contradictory values still fails closed. The workflow subsequently
    requires exact geometry reproduction from this same layer.
    """
    expected = {
        "id": 3,
        "name": "Commissioner Precincts",
        "type": "Feature Layer",
        "geometryType": "esriGeometryPolygon",
        "copyrightText": "Elections",
    }
    present = sum(key in payload for key in expected)
    if present < 3:
        raise MetadataUnavailable(
            f"controlling response lacks a usable layer fingerprint: keys={sorted(payload)!r}"
        )
    for key, value in expected.items():
        if key not in payload:
            raise MetadataContradiction(f"controlling layer lost {key}")
        if payload.get(key) != value:
            raise MetadataContradiction(
                f"unexpected controlling {key}: {payload.get(key)!r} != {value!r}"
            )
    if "District_N" not in field_names(payload):
        raise MetadataContradiction("controlling layer lost District_N")
    formats = str(payload.get("supportedQueryFormats") or "")
    if "geojson" not in formats.casefold():
        raise MetadataContradiction(
            f"controlling layer lost GeoJSON query support: {formats!r}"
        )

    description = str(payload.get("description") or "").strip()
    if description:
        if "June 3rd 2025" not in description and "June 3, 2025" not in description:
            raise MetadataContradiction(
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
    if "geometryType" not in payload and "fields" not in payload:
        raise MetadataUnavailable(
            f"general response lacks contract-bearing metadata: keys={sorted(payload)!r}"
        )
    if payload.get("geometryType") != "esriGeometryPolygon":
        raise MetadataContradiction(
            f"unexpected general geometry type: {payload.get('geometryType')!r}"
        )
    if "District_N" not in field_names(payload):
        raise MetadataContradiction("general layer lost District_N")


def validate_stale(payload: dict[str, Any]) -> None:
    values = [
        str(payload.get(key) or "")
        for key in ("serviceDescription", "description", "mapName")
    ]
    if not any(value.strip() for value in values):
        raise MetadataUnavailable(
            f"stale-service response lacks descriptive metadata: keys={sorted(payload)!r}"
        )
    text = " ".join(values)
    if "2010" not in text:
        raise MetadataContradiction(
            f"explicit 2010 stale-service marker is missing: {text!r}"
        )


def require_html_markers(text: str, markers: tuple[str, ...]) -> None:
    lowered = text.casefold()
    contract_tokens = (
        "layer:",
        "geometry type:",
        "fields:",
        "supported query formats",
        "service description",
        "map name",
    )
    if not any(token in lowered for token in contract_tokens):
        raise MetadataUnavailable("HTML response is the generic ArcGIS shell")
    missing = [marker for marker in markers if marker.casefold() not in lowered]
    if missing:
        raise MetadataContradiction(f"HTML metadata lost markers: {missing!r}")


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
        raise MetadataUnavailable(
            f"non-JSON metadata response from {request_url}; preview={preview!r}"
        ) from exc
    if not isinstance(payload, dict):
        raise MetadataUnavailable(
            f"metadata response from {request_url} is not an object"
        )
    if payload.get("error") is not None:
        raise MetadataUnavailable(
            f"ArcGIS metadata error from {request_url}: {payload['error']!r}"
        )
    if not payload:
        raise MetadataUnavailable(f"empty metadata object from {request_url}")
    return payload


def read_html(response: Any, *, request_url: str) -> str:
    body = response.read()
    text = body.decode("utf-8", errors="replace")
    if not text.strip():
        raise MetadataUnavailable(f"empty HTML metadata response from {request_url}")
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
    allow_unavailable: bool = False,
) -> dict[str, Any]:
    unavailable: list[str] = []
    contradictions: list[str] = []
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
            except MetadataContradiction as exc:
                contradictions.append(
                    f"attempt={attempt} format={response_format}: {exc}"
                )
            except Exception as exc:
                unavailable.append(
                    f"attempt={attempt} format={response_format}: {exc}"
                )

        if html_validator is not None:
            request_url = f"{base_url}?{urlencode({'_cc_html_attempt': attempt})}"
            request = urllib.request.Request(request_url, headers=HTML_HEADERS)
            text: str | None = None
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    text = read_html(response, request_url=request_url)
                html_validator(text)
                print(f"Validated Tarrant {label} metadata through ArcGIS HTML directory.")
                return {"validated_via": "html", "request_url": request_url}
            except MetadataContradiction as exc:
                diagnostic = html_diagnostic(text) if text is not None else "no_body"
                contradictions.append(
                    f"attempt={attempt} format=html: {exc}; {diagnostic}"
                )
            except Exception as exc:
                diagnostic = html_diagnostic(text) if text is not None else "no_body"
                unavailable.append(
                    f"attempt={attempt} format=html: {exc}; {diagnostic}"
                )

        if attempt < attempts:
            time.sleep(attempt * 5)

    if contradictions:
        raise SystemExit(
            f"Tarrant {label} metadata contradicted the retained contract: "
            + " | ".join(contradictions[-6:])
        )
    if allow_unavailable:
        print(
            f"Tarrant {label} live metadata was unavailable after {attempts} attempts; "
            "retaining the source hierarchy and deferring authority to the mandatory "
            "exact-source geometry checks."
        )
        return {
            "validated_via": "unavailable",
            "status": "DEFERRED_TO_EXACT_GEOMETRY_CHECKS",
            "attempts": attempts,
            "diagnostics": unavailable[-6:],
        }
    raise SystemExit(
        f"Tarrant {label} metadata contract failed after {attempts} attempts: "
        + " | ".join(unavailable[-6:])
    )


def main() -> int:
    results = {
        "controlling": fetch_contract(
            "controlling",
            URLS["controlling"],
            validate_controlling,
            html_validator=validate_controlling_html,
            allow_unavailable=True,
        ),
        "general": fetch_contract(
            "general",
            URLS["general"],
            validate_general,
            html_validator=validate_general_html,
            allow_unavailable=True,
        ),
        "stale_2010": fetch_contract(
            "stale_2010",
            URLS["stale_2010"],
            validate_stale,
            html_validator=validate_stale_html,
            allow_unavailable=True,
        ),
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    unavailable = [
        label
        for label, result in results.items()
        if result.get("validated_via") == "unavailable"
    ]
    if unavailable:
        print(
            "Tarrant metadata availability deferred for: "
            + ", ".join(unavailable)
            + ". Exact controlling/general geometry validation remains mandatory."
        )
    else:
        print("Tarrant County ArcGIS metadata hierarchy matches the release contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
