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


def normalize_snapshot(payload: dict[str, Any], *, canonical: bool) -> dict[str, Any]:
    """Remove only non-geographic ArcGIS bookkeeping fields."""
    normalized = copy.deepcopy(payload)
    features = normalized.get("features")
    if normalized.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise ValueError("snapshot must be a GeoJSON FeatureCollection")
    if len(features) != 1:
        raise ValueError(f"snapshot must contain exactly one feature; found {len(features)}")

    feature = features[0]
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError("snapshot feature must be a GeoJSON Feature")

    # ArcGIS may emit a service-local feature id derived from OBJECTID.
    feature.pop("id", None)
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("snapshot feature properties must be an object")

    source_properties = properties.get("source_attributes") if canonical else properties
    if not isinstance(source_properties, dict):
        if canonical:
            raise ValueError("canonical snapshot must include source_attributes")
        raise ValueError("raw snapshot properties must be an object")

    for field in VOLATILE_SOURCE_FIELDS:
        source_properties.pop(field, None)

    return normalized


def compare_files(
    committed: Path,
    fresh: Path,
    *,
    canonical: bool,
) -> list[str]:
    errors: list[str] = []
    try:
        committed_payload = normalize_snapshot(load_json(committed), canonical=canonical)
        fresh_payload = normalize_snapshot(load_json(fresh), canonical=canonical)
    except ValueError as exc:
        return [str(exc)]

    if committed_payload != fresh_payload:
        kind = "canonical" if canonical else "raw"
        errors.append(
            f"{kind} TIGERweb snapshot changed: {committed} does not match {fresh}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed-raw", type=Path, required=True)
    parser.add_argument("--fresh-raw", type=Path, required=True)
    parser.add_argument("--committed-canonical", type=Path, required=True)
    parser.add_argument("--fresh-canonical", type=Path, required=True)
    args = parser.parse_args()

    errors = compare_files(args.committed_raw, args.fresh_raw, canonical=False)
    errors.extend(
        compare_files(
            args.committed_canonical,
            args.fresh_canonical,
            canonical=True,
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
