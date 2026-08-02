#!/usr/bin/env python3
"""Fetch selected district polygons from an ArcGIS feature layer."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = (
    "Civic-Cartography/0.1 "
    "(+https://github.com/MightyLoud/Civic-Cartography)"
)
VOLATILE_FIELD_NAMES = {
    "OBJECTID",
    "OID",
    "FID",
    "GLOBALID",
    "SHAPE__AREA",
    "SHAPE__LENGTH",
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def normalize_identifier(value: Any) -> str | None:
    """Return one district number from common ArcGIS property values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else None

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+", text):
        return str(int(text))

    matches = re.findall(r"(?<!\d)(\d{1,3})(?!\d)", text)
    if len(matches) == 1:
        return str(int(matches[0]))
    return None


def fetch_layer(
    layer_url: str,
    *,
    out_fields: str = "*",
    geometry_precision: int | None = None,
    timeout: int = 60,
) -> tuple[dict[str, Any], str]:
    """Fetch all layer features as WGS84 GeoJSON."""
    query_url = f"{layer_url.rstrip('/')}/query"
    params = {
        "where": "1=1",
        "outFields": out_fields,
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    if geometry_precision is not None:
        params["geometryPrecision"] = str(geometry_precision)

    request_url = f"{query_url}?{urlencode(params)}"
    request = Request(request_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    features = payload.get("features")
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise ValueError("ArcGIS response must be a GeoJSON FeatureCollection")
    if not features:
        raise ValueError("ArcGIS response contained no features")
    return payload, request_url


def infer_district_field(
    features: list[dict[str, Any]], expected_ids: set[str]
) -> str:
    """Identify the stable property that uniquely represents district numbers."""
    property_keys: set[str] = set()
    for feature in features:
        properties = feature.get("properties")
        if isinstance(properties, dict):
            property_keys.update(str(key) for key in properties)

    candidates: list[tuple[int, str]] = []
    for key in sorted(property_keys):
        upper_key = key.upper()
        if upper_key in VOLATILE_FIELD_NAMES or upper_key.endswith("OBJECTID"):
            continue

        counts: dict[str, int] = {}
        for feature in features:
            properties = feature.get("properties") or {}
            identifier = normalize_identifier(properties.get(key))
            if identifier is not None:
                counts[identifier] = counts.get(identifier, 0) + 1

        if not expected_ids.issubset(counts):
            continue
        if any(counts[identifier] != 1 for identifier in expected_ids):
            continue

        score = 0
        if "DISTRICT" in upper_key:
            score += 100
        elif "DIST" in upper_key:
            score += 80
        if "PRECINCT" in upper_key:
            score += 100
        elif "PCT" in upper_key:
            score += 80
        if "COUNCIL" in upper_key:
            score += 40
        if upper_key in {"ID", "NUMBER", "NO", "NUM"}:
            score -= 30
        candidates.append((score, key))

    if not candidates:
        raise ValueError(
            "Unable to infer a unique district field for IDs: "
            + ", ".join(sorted(expected_ids, key=int))
        )

    candidates.sort(key=lambda item: (-item[0], item[1]))
    best_score = candidates[0][0]
    best = [key for score, key in candidates if score == best_score]
    if len(best) != 1:
        raise ValueError(
            "Ambiguous district fields with equal score: " + ", ".join(best)
        )
    return best[0]


def select_features(
    payload: dict[str, Any], *, district_field: str, expected_ids: set[str]
) -> dict[str, Any]:
    """Return only the requested district features in numeric order."""
    selected: list[tuple[int, dict[str, Any]]] = []
    for feature in payload["features"]:
        properties = feature.get("properties") or {}
        district_id = normalize_identifier(properties.get(district_field))
        if district_id not in expected_ids:
            continue

        geometry = feature.get("geometry")
        geometry_type = geometry.get("type") if isinstance(geometry, dict) else None
        if geometry_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(
                f"District {district_id} has unsupported geometry {geometry_type!r}"
            )
        selected.append((int(district_id), copy.deepcopy(feature)))

    selected.sort(key=lambda item: item[0])
    found = {str(number) for number, _ in selected}
    if found != expected_ids:
        raise ValueError(
            "Selected district IDs did not match expected IDs; found "
            + ", ".join(sorted(found, key=int))
        )
    return {"type": "FeatureCollection", "features": [f for _, f in selected]}


def canonicalize(
    raw_payload: dict[str, Any],
    *,
    district_field: str,
    jurisdiction_name: str,
    record_id_prefix: str,
    geometry_id_prefix: str,
    source_agency: str,
    layer_url: str,
    request_url: str,
    retrieved_at: str,
    district_type: str = "district",
    district_name_prefix: str = "District",
) -> dict[str, Any]:
    """Create map-ready features with stable join identifiers."""
    canonical_features: list[dict[str, Any]] = []
    for source_feature in raw_payload["features"]:
        source_properties = source_feature.get("properties") or {}
        district_id = normalize_identifier(source_properties.get(district_field))
        if district_id is None:
            raise ValueError(f"Blank district ID in source field {district_field!r}")

        canonical_features.append(
            {
                "type": "Feature",
                "properties": {
                    "geometry_id": f"{geometry_id_prefix}-{district_id}",
                    "record_id": f"{record_id_prefix}:{district_id}",
                    "jurisdiction_name": jurisdiction_name,
                    "district_type": district_type,
                    "district_id": district_id,
                    "district_name": f"{district_name_prefix} {district_id}",
                    "source_agency": source_agency,
                    "source_layer": layer_url,
                    "source_request_url": request_url,
                    "source_retrieved_at": retrieved_at,
                    "source_district_field": district_field,
                    "source_attributes": source_properties,
                },
                "geometry": source_feature["geometry"],
            }
        )

    canonical_features.sort(
        key=lambda feature: int(feature["properties"]["district_id"])
    )
    return {"type": "FeatureCollection", "features": canonical_features}


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
    parser.add_argument(
        "--out-fields",
        default="*",
        help="Comma-separated ArcGIS attributes to request; defaults to all fields.",
    )
    parser.add_argument(
        "--geometry-precision",
        type=int,
        help="Optional ArcGIS geometryPrecision value for slow or oversized layers.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="ArcGIS request timeout in seconds; defaults to 60.",
    )
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

    payload, request_url = fetch_layer(
        args.layer_url,
        out_fields=args.out_fields,
        geometry_precision=args.geometry_precision,
        timeout=args.timeout,
    )
    district_field = args.district_field or infer_district_field(
        payload["features"], expected_ids
    )
    raw_payload = select_features(
        payload, district_field=district_field, expected_ids=expected_ids
    )
    canonical = canonicalize(
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

    write_json(args.raw_output, raw_payload)
    write_json(args.output, canonical)
    print(
        f"Wrote {len(canonical['features'])} district features using "
        f"source field {district_field!r}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
