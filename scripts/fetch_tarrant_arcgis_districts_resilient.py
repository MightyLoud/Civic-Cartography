#!/usr/bin/env python3
"""Fetch Tarrant district polygons with an exact-source object-ID fallback.

The canonical all-features GeoJSON request remains first.  If the same official
ArcGIS layer returns HTML, truncated JSON, or an error envelope, this wrapper
requests object IDs and then fetches bounded GeoJSON chunks from that identical
`/query` endpoint.  No alternate layer or stale source is accepted.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from scripts import fetch_arcgis_districts as shared

USER_AGENT = "Mozilla/5.0 Civic-Cartography-validator/1.0"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/geo+json,application/json,text/plain,*/*",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def canonical_request_url(layer_url: str) -> str:
    query_url = f"{layer_url.rstrip('/')}/query"
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    return f"{query_url}?{urlencode(params)}"


def read_json(response: Any, *, method: str, request_url: str) -> dict[str, Any]:
    body = response.read()
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = " ".join(body[:240].decode("utf-8", errors="replace").split())
        raise ValueError(
            f"ArcGIS {method} returned non-JSON content from {request_url}; "
            f"preview={preview!r}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"ArcGIS {method} response from {request_url} is not an object"
        )
    if payload.get("error") is not None:
        raise ValueError(
            f"ArcGIS {method} error from {request_url}: {payload['error']!r}"
        )
    return payload


def request_json(
    query_url: str,
    params: dict[str, str],
    *,
    expected: str,
) -> dict[str, Any]:
    encoded = urlencode(params)
    requests = (
        (
            "GET",
            urllib.request.Request(
                f"{query_url}?{encoded}",
                headers=HEADERS,
                method="GET",
            ),
        ),
        (
            "POST",
            urllib.request.Request(
                query_url,
                data=encoded.encode("ascii"),
                headers={
                    **HEADERS,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            ),
        ),
    )
    errors: list[str] = []
    for method, request in requests:
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = read_json(
                    response,
                    method=method,
                    request_url=request.full_url,
                )
            if expected == "object_ids":
                ids = payload.get("objectIds")
                if not isinstance(ids, list) or not ids:
                    raise ValueError("response contains no objectIds")
            elif expected == "geojson":
                features = payload.get("features")
                if payload.get("type") != "FeatureCollection" or not isinstance(
                    features, list
                ):
                    raise ValueError("response is not a GeoJSON FeatureCollection")
                if not features:
                    raise ValueError("GeoJSON FeatureCollection contains no features")
            else:
                raise AssertionError(expected)
            return payload
        except Exception as exc:
            errors.append(f"{method}: {exc}")
    raise ValueError(
        f"ArcGIS {expected} request failed through both equivalent transports: "
        + " | ".join(errors)
    )


def fetch_by_object_ids(
    layer_url: str,
    *,
    chunk_size: int = 25,
) -> tuple[dict[str, Any], str]:
    """Fetch one layer through bounded object-ID chunks from the same endpoint."""
    query_url = f"{layer_url.rstrip('/')}/query"
    ids_payload = request_json(
        query_url,
        {
            "where": "1=1",
            "returnIdsOnly": "true",
            "f": "json",
        },
        expected="object_ids",
    )
    object_ids = sorted({int(value) for value in ids_payload["objectIds"]})
    if not object_ids:
        raise ValueError("ArcGIS object-ID fallback returned no IDs")

    combined: list[dict[str, Any]] = []
    for offset in range(0, len(object_ids), chunk_size):
        chunk = object_ids[offset : offset + chunk_size]
        payload = request_json(
            query_url,
            {
                "objectIds": ",".join(str(value) for value in chunk),
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            },
            expected="geojson",
        )
        combined.extend(payload["features"])

    if not combined:
        raise ValueError("ArcGIS object-ID fallback assembled no features")

    feature_ids = [feature.get("id") for feature in combined]
    concrete_ids = [value for value in feature_ids if value is not None]
    if len(concrete_ids) != len(set(concrete_ids)):
        raise ValueError("ArcGIS object-ID fallback produced duplicate feature IDs")

    return (
        {"type": "FeatureCollection", "features": combined},
        canonical_request_url(layer_url),
    )


def fetch_layer_resilient(layer_url: str) -> tuple[dict[str, Any], str]:
    canonical_error: Exception | None = None
    try:
        return shared.fetch_layer(layer_url)
    except Exception as exc:
        canonical_error = exc

    try:
        payload, request_url = fetch_by_object_ids(layer_url)
    except Exception as fallback_error:
        raise ValueError(
            "Tarrant exact-layer fetch failed through canonical and object-ID "
            f"transports; canonical={canonical_error}; fallback={fallback_error}"
        ) from fallback_error

    print(
        "Canonical all-features GeoJSON transport was unavailable; reproduced "
        "the identical official layer through bounded object-ID chunks."
    )
    return payload, request_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer-url", required=True)
    parser.add_argument("--district-ids", required=True)
    parser.add_argument("--district-field")
    parser.add_argument("--district-type", default="district")
    parser.add_argument("--district-name-prefix", default="District")
    parser.add_argument("--jurisdiction-name", required=True)
    parser.add_argument("--record-id-prefix", required=True)
    parser.add_argument("--geometry-id-prefix", required=True)
    parser.add_argument("--source-agency", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    expected_ids = {
        str(int(value.strip()))
        for value in args.district_ids.split(",")
        if value.strip()
    }
    if not expected_ids:
        raise ValueError("--district-ids must contain at least one district number")

    payload, request_url = fetch_layer_resilient(args.layer_url)
    district_field = args.district_field or shared.infer_district_field(
        payload["features"], expected_ids
    )
    raw_payload = shared.select_features(
        payload,
        district_field=district_field,
        expected_ids=expected_ids,
    )
    canonical = shared.canonicalize(
        raw_payload,
        district_field=district_field,
        jurisdiction_name=args.jurisdiction_name,
        record_id_prefix=args.record_id_prefix,
        geometry_id_prefix=args.geometry_id_prefix,
        source_agency=args.source_agency,
        layer_url=args.layer_url,
        request_url=request_url,
        retrieved_at=args.retrieved_at,
        district_type=args.district_type,
        district_name_prefix=args.district_name_prefix,
    )

    shared.write_json(args.raw_output, raw_payload)
    shared.write_json(args.output, canonical)
    print(
        f"Wrote {len(canonical['features'])} district features using "
        f"source field {district_field!r}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
