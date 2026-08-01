#!/usr/bin/env python3
"""Fetch one unified-school-district boundary from U.S. Census TIGERweb."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LAYER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/tigerWMS_Current/MapServer/14"
)
QUERY_URL = f"{LAYER_URL}/query"


def _escape_sql(value: str) -> str:
    return value.replace("'", "''")


def fetch_school_district(name_token: str) -> tuple[dict, str]:
    """Return exactly one current unified-school-district feature."""
    token = name_token.strip()
    if not token:
        raise ValueError("name_token must not be blank")

    params = {
        "where": f"BASENAME LIKE '%{_escape_sql(token)}%'",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    request_url = f"{QUERY_URL}?{urlencode(params)}"
    request = Request(
        request_url,
        headers={
            "User-Agent": (
                "Civic-Cartography/0.1 "
                "(+https://github.com/MightyLoud/Civic-Cartography)"
            )
        },
    )
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)

    features = payload.get("features")
    feature_count = len(features) if isinstance(features, list) else 0
    if feature_count != 1:
        raise ValueError(
            f"Expected one unified school district matching {token!r}; "
            f"received {feature_count}"
        )

    feature = features[0]
    properties = feature.get("properties") or {}
    basename = str(properties.get("BASENAME") or "").strip()
    if token.casefold() not in basename.casefold():
        raise ValueError(
            f"TIGERweb returned BASENAME {basename!r}; expected it to contain {token!r}"
        )

    geoid = str(properties.get("GEOID") or "").strip()
    if not geoid:
        raise ValueError("TIGERweb school district feature has no GEOID")

    geometry = feature.get("geometry")
    geometry_type = geometry.get("type") if isinstance(geometry, dict) else None
    if geometry_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(
            f"Unsupported or missing geometry for unified school district {basename!r}"
        )

    return payload, request_url


def canonicalize(
    raw_payload: dict,
    *,
    record_id: str,
    geometry_id: str,
    retrieved_at: str,
    request_url: str,
) -> dict:
    """Add stable repository join and source properties to the district feature."""
    source_feature = raw_payload["features"][0]
    source_properties = source_feature.get("properties") or {}
    name = str(source_properties.get("BASENAME") or "Unknown").strip()

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "geometry_id": geometry_id,
                    "record_id": record_id,
                    "jurisdiction_name": name,
                    "jurisdiction_type": "school_district",
                    "district_type": "at_large",
                    "district_id": "DISTRICTWIDE",
                    "district_name": "Districtwide",
                    "census_geoid": str(source_properties.get("GEOID") or ""),
                    "source_agency": "U.S. Census Bureau",
                    "source_layer": LAYER_URL,
                    "source_request_url": request_url,
                    "source_vintage": "2025-01-01",
                    "source_retrieved_at": retrieved_at,
                    "source_attributes": source_properties,
                },
                "geometry": source_feature["geometry"],
            }
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name-token", required=True)
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--geometry-id", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path)
    args = parser.parse_args()

    raw_payload, request_url = fetch_school_district(args.name_token)
    if args.raw_output:
        write_json(args.raw_output, raw_payload)

    canonical = canonicalize(
        raw_payload,
        record_id=args.record_id,
        geometry_id=args.geometry_id,
        retrieved_at=args.retrieved_at,
        request_url=request_url,
    )
    write_json(args.output, canonical)

    properties = canonical["features"][0]["properties"]
    print(
        "Wrote one map-ready school district feature "
        f"for GEOID {properties['census_geoid']} to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
