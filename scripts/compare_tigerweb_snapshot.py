#!/usr/bin/env python3
"""Compare committed and freshly fetched TIGERweb GeoJSON snapshots."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

# ArcGIS service bookkeeping can change without changing the civic geography.
VOLATILE_SOURCE_FIELDS = {"OBJECTID", "OID", "DISP_CLR"}
# Census changed these integer-valued fields from JSON strings to numbers.
# Normalize representation only; every actual area value remains significant.
INTEGER_SOURCE_FIELDS = {"AREALAND", "AREAWATER"}


def stable_attributes(properties: dict[str, Any]) -> dict[str, Any]:
    for field in VOLATILE_SOURCE_FIELDS:
        properties.pop(field, None)
    for field in INTEGER_SOURCE_FIELDS:
        if field not in properties:
            continue
        value = properties[field]
        if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
            properties[field] = int(value)
        elif type(value) is not int or value < 0:
            raise ValueError(f"TIGERweb source attribute {field} must be a nonnegative integer")
    return properties


def changed_fields(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return sorted(
        field for field in left.keys() | right.keys()
        if field not in left or field not in right or left[field] != right[field]
    )


def drift_details(left: dict[str, Any], right: dict[str, Any], *, canonical: bool) -> str:
    if canonical:
        left = left["features"][0]
        right = right["features"][0]
    details = []
    if left["geometry"] != right["geometry"]:
        details.append("geometry changed")
    left_properties = left["properties"].copy()
    right_properties = right["properties"].copy()
    if canonical:
        fields = changed_fields(
            left_properties.pop("source_attributes"),
            right_properties.pop("source_attributes"),
        )
        if fields:
            details.append(f"source attributes changed: {', '.join(fields)}")
    fields = changed_fields(left_properties, right_properties)
    if fields:
        label = "canonical properties" if canonical else "source attributes"
        details.append(f"{label} changed: {', '.join(fields)}")
    return "; ".join(details)


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unable to read valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON root must be an object")
    return payload


def extract_feature(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    features = payload.get("features")
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise ValueError("snapshot must be a GeoJSON FeatureCollection")
    if len(features) != 1:
        raise ValueError(f"snapshot must contain exactly one feature; found {len(features)}")

    feature = features[0]
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError("snapshot feature must be a GeoJSON Feature")

    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict):
        raise ValueError("snapshot feature properties must be an object")
    if not isinstance(geometry, dict):
        raise ValueError("snapshot feature geometry must be an object")
    return properties, geometry


def stable_source_view(payload: dict[str, Any], *, canonical: bool) -> dict[str, Any]:
    """Return source attributes and geometry, excluding service bookkeeping."""
    properties, geometry = extract_feature(copy.deepcopy(payload))
    source_properties = properties.get("source_attributes") if canonical else properties
    if not isinstance(source_properties, dict):
        if canonical:
            raise ValueError("canonical snapshot must include source_attributes")
        raise ValueError("raw snapshot properties must be an object")

    stable_attributes(source_properties)

    return {
        "properties": source_properties,
        "geometry": geometry,
    }


def stable_canonical_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Return canonical join, attribution, source attributes, and geometry."""
    properties, geometry = extract_feature(copy.deepcopy(payload))
    source_properties = properties.get("source_attributes")
    if not isinstance(source_properties, dict):
        raise ValueError("canonical snapshot must include source_attributes")
    stable_attributes(source_properties)

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": properties,
                "geometry": geometry,
            }
        ],
    }


def compare_raw_and_canonical(raw_path: Path, canonical_path: Path) -> list[str]:
    try:
        raw_view = stable_source_view(load_json(raw_path), canonical=False)
        canonical_view = stable_source_view(load_json(canonical_path), canonical=True)
    except ValueError as exc:
        return [str(exc)]

    if raw_view != canonical_view:
        return [
            f"raw and canonical snapshots disagree: {raw_path} does not support "
            f"{canonical_path}; {drift_details(raw_view, canonical_view, canonical=False)}"
        ]
    return []


def compare_canonical_files(committed: Path, fresh: Path) -> list[str]:
    try:
        committed_view = stable_canonical_view(load_json(committed))
        fresh_view = stable_canonical_view(load_json(fresh))
    except ValueError as exc:
        return [str(exc)]

    if committed_view != fresh_view:
        return [
            f"canonical TIGERweb snapshot changed: {committed} does not match {fresh}; "
            f"{drift_details(committed_view, fresh_view, canonical=True)}"
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed-raw", type=Path, required=True)
    parser.add_argument("--fresh-raw", type=Path, required=True)
    parser.add_argument("--committed-canonical", type=Path, required=True)
    parser.add_argument("--fresh-canonical", type=Path, required=True)
    args = parser.parse_args()

    errors = compare_raw_and_canonical(
        args.committed_raw,
        args.committed_canonical,
    )
    errors.extend(
        compare_raw_and_canonical(
            args.fresh_raw,
            args.fresh_canonical,
        )
    )
    errors.extend(
        compare_canonical_files(
            args.committed_canonical,
            args.fresh_canonical,
        )
    )

    if errors:
        print("TIGERweb snapshot comparison failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Committed TIGERweb snapshots match the current civic geography.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
