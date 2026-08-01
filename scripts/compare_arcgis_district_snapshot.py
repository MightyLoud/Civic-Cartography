#!/usr/bin/env python3
"""Validate committed ArcGIS district evidence against a fresh official fetch."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from scripts.fetch_arcgis_districts import normalize_identifier

VOLATILE_SOURCE_FIELDS = {
    "OBJECTID",
    "OID",
    "FID",
    "GLOBALID",
    "SHAPE__AREA",
    "SHAPE__LENGTH",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unable to read valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return payload


def feature_collection(payload: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    features = payload.get("features")
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise ValueError(f"{label}: must be a GeoJSON FeatureCollection")
    if not features:
        raise ValueError(f"{label}: must contain at least one feature")
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"{label}: every item must be a GeoJSON Feature")
    return features


def stable_attributes(properties: dict[str, Any]) -> dict[str, Any]:
    stable = copy.deepcopy(properties)
    for key in list(stable):
        if key.upper() in VOLATILE_SOURCE_FIELDS or key.upper().endswith("OBJECTID"):
            stable.pop(key, None)
    return stable


def raw_by_district(
    payload: dict[str, Any], *, district_field: str, label: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for feature in feature_collection(payload, label=label):
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"{label}: feature properties must be an object")
        district_id = normalize_identifier(properties.get(district_field))
        if district_id is None:
            raise ValueError(
                f"{label}: unable to read district ID from {district_field!r}"
            )
        if district_id in indexed:
            raise ValueError(f"{label}: duplicate district ID {district_id}")
        indexed[district_id] = {
            "properties": stable_attributes(properties),
            "geometry": feature.get("geometry"),
        }
    return indexed


def canonical_by_district(
    payload: dict[str, Any], *, label: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for feature in feature_collection(payload, label=label):
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"{label}: feature properties must be an object")
        district_id = normalize_identifier(properties.get("district_id"))
        if district_id is None:
            raise ValueError(f"{label}: blank canonical district_id")
        source_attributes = properties.get("source_attributes")
        if not isinstance(source_attributes, dict):
            raise ValueError(f"{label}: canonical feature lacks source_attributes")
        if district_id in indexed:
            raise ValueError(f"{label}: duplicate district ID {district_id}")

        stable_feature = copy.deepcopy(feature)
        stable_feature.pop("id", None)
        stable_feature["properties"]["source_attributes"] = stable_attributes(
            source_attributes
        )
        indexed[district_id] = stable_feature
    return indexed


def compare_raw_to_canonical(
    raw_payload: dict[str, Any],
    canonical_payload: dict[str, Any],
    *,
    raw_label: str,
    canonical_label: str,
) -> list[str]:
    errors: list[str] = []
    canonical = canonical_by_district(canonical_payload, label=canonical_label)
    district_fields = {
        str(feature["properties"].get("source_district_field") or "")
        for feature in canonical.values()
    }
    district_fields.discard("")
    if len(district_fields) != 1:
        return [f"{canonical_label}: expected one source_district_field"]
    district_field = next(iter(district_fields))
    raw = raw_by_district(raw_payload, district_field=district_field, label=raw_label)

    if set(raw) != set(canonical):
        errors.append(
            f"{raw_label} and {canonical_label} district IDs differ: "
            f"raw={sorted(raw, key=int)} canonical={sorted(canonical, key=int)}"
        )
        return errors

    for district_id in sorted(raw, key=int):
        canonical_feature = canonical[district_id]
        canonical_properties = canonical_feature["properties"]
        if raw[district_id]["properties"] != canonical_properties["source_attributes"]:
            errors.append(
                f"District {district_id}: raw source attributes do not support canonical"
            )
        if raw[district_id]["geometry"] != canonical_feature.get("geometry"):
            errors.append(
                f"District {district_id}: raw geometry does not support canonical"
            )
    return errors


def compare_canonical_snapshots(
    committed_payload: dict[str, Any], fresh_payload: dict[str, Any]
) -> list[str]:
    committed = canonical_by_district(committed_payload, label="committed canonical")
    fresh = canonical_by_district(fresh_payload, label="fresh canonical")
    if committed != fresh:
        return ["Committed canonical district geometry differs from the current source"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed-raw", type=Path, required=True)
    parser.add_argument("--fresh-raw", type=Path, required=True)
    parser.add_argument("--committed-canonical", type=Path, required=True)
    parser.add_argument("--fresh-canonical", type=Path, required=True)
    args = parser.parse_args()

    try:
        committed_raw = load_json(args.committed_raw)
        fresh_raw = load_json(args.fresh_raw)
        committed_canonical = load_json(args.committed_canonical)
        fresh_canonical = load_json(args.fresh_canonical)

        errors = compare_raw_to_canonical(
            committed_raw,
            committed_canonical,
            raw_label="committed raw",
            canonical_label="committed canonical",
        )
        errors.extend(
            compare_raw_to_canonical(
                fresh_raw,
                fresh_canonical,
                raw_label="fresh raw",
                canonical_label="fresh canonical",
            )
        )
        errors.extend(
            compare_canonical_snapshots(committed_canonical, fresh_canonical)
        )
    except ValueError as exc:
        errors = [str(exc)]

    if errors:
        print("ArcGIS district snapshot validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Committed ArcGIS district snapshots match the current official source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
