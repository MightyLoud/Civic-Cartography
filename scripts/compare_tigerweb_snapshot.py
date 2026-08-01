#!/usr/bin/env python3
"""Compare committed and freshly fetched TIGERweb GeoJSON snapshots."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

# ArcGIS service bookkeeping can change without changing the civic geography.
VOLATILE_SOURCE_FIELDS = {"OBJECTID", "OID", "DISP_CLR"}


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

    for field in VOLATILE_SOURCE_FIELDS:
        source_properties.pop(field, None)

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
    for field in VOLATILE_SOURCE_FIELDS:
        source_properties.pop(field, None)

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
            f"{canonical_path}"
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
            f"canonical TIGERweb snapshot changed: {committed} does not match {fresh}"
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
