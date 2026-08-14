#!/usr/bin/env python3
"""Validate the Tarrant County ArcGIS source hierarchy with bounded retries."""

from __future__ import annotations

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
Validator = Callable[[dict[str, Any]], None]


def field_names(payload: dict[str, Any]) -> set[str]:
    return {
        str(field.get("name"))
        for field in payload.get("fields", [])
        if isinstance(field, dict) and field.get("name") is not None
    }


def validate_controlling(payload: dict[str, Any]) -> None:
    description = str(payload.get("description") or "")
    if "June 3rd 2025" not in description and "June 3, 2025" not in description:
        raise ValueError(
            f"controlling layer lost effective-date description: {description!r}"
        )
    if payload.get("geometryType") != "esriGeometryPolygon":
        raise ValueError(
            f"unexpected controlling geometry type: {payload.get('geometryType')!r}"
        )
    if "District_N" not in field_names(payload):
        raise ValueError("controlling layer lost District_N")


def validate_general(payload: dict[str, Any]) -> None:
    if "District_N" not in field_names(payload):
        raise ValueError("general layer lost District_N")


def validate_stale(payload: dict[str, Any]) -> None:
    text = " ".join(
        str(payload.get(key) or "")
        for key in ("serviceDescription", "description", "mapName")
    )
    if "2010" not in text:
        raise ValueError(f"explicit 2010 stale-service marker is missing: {text!r}")


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


def fetch_contract(
    label: str,
    base_url: str,
    validator: Validator,
    *,
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
                return payload
            except Exception as exc:
                errors.append(
                    f"attempt={attempt} format={response_format}: {exc}"
                )
        if attempt < attempts:
            time.sleep(attempt * 5)
    raise SystemExit(
        f"Tarrant {label} metadata contract failed after {attempts} attempts: "
        + " | ".join(errors[-4:])
    )


def main() -> int:
    fetch_contract("controlling", URLS["controlling"], validate_controlling)
    fetch_contract("general", URLS["general"], validate_general)
    fetch_contract("stale_2010", URLS["stale_2010"], validate_stale)
    print("Tarrant County ArcGIS metadata hierarchy matches the release contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
