#!/usr/bin/env python3
"""Validate normalized-record to GeoJSON geometry joins."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def load_normalized_geometry_ids(
    normalized_dir: Path,
) -> tuple[dict[str, str], list[str]]:
    joins: dict[str, str] = {}
    errors: list[str] = []

    for path in sorted(normalized_dir.glob("*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for line_number, row in enumerate(reader, start=2):
                geometry_id = (row.get("geometry_id") or "").strip()
                record_id = (row.get("record_id") or "").strip()
                if not geometry_id:
                    continue
                if not record_id:
                    errors.append(f"{path}:{line_number}: geometry_id has no record_id")
                    continue

                prior = joins.get(geometry_id)
                if prior and prior != record_id:
                    errors.append(
                        f"{path}:{line_number}: geometry_id '{geometry_id}' "
                        f"is assigned to both '{prior}' and '{record_id}'"
                    )
                else:
                    joins[geometry_id] = record_id

    return joins, errors


def load_geojson_features(
    geojson_dir: Path,
) -> tuple[dict[str, str], list[str]]:
    features_by_id: dict[str, str] = {}
    errors: list[str] = []

    for path in sorted(geojson_dir.glob("*.geojson")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: unable to read valid GeoJSON: {exc}")
            continue

        if payload.get("type") != "FeatureCollection":
            errors.append(f"{path}: root type must be FeatureCollection")
            continue

        features = payload.get("features")
        if not isinstance(features, list):
            errors.append(f"{path}: features must be a list")
            continue

        for index, feature in enumerate(features, start=1):
            prefix = f"{path}:feature[{index}]"
            if feature.get("type") != "Feature":
                errors.append(f"{prefix}: type must be Feature")
                continue

            properties = feature.get("properties") or {}
            geometry_id = str(properties.get("geometry_id") or "").strip()
            record_id = str(properties.get("record_id") or "").strip()
            if not geometry_id:
                errors.append(f"{prefix}: blank properties.geometry_id")
                continue
            if not record_id:
                errors.append(f"{prefix}: blank properties.record_id")

            geometry = feature.get("geometry")
            geometry_type = geometry.get("type") if isinstance(geometry, dict) else None
            if geometry_type not in {"Polygon", "MultiPolygon"}:
                errors.append(
                    f"{prefix}: geometry type must be Polygon or MultiPolygon"
                )

            if geometry_id in features_by_id:
                errors.append(f"{prefix}: duplicate geometry_id '{geometry_id}'")
            else:
                features_by_id[geometry_id] = record_id

    return features_by_id, errors


def validate_join(normalized_dir: Path, geojson_dir: Path) -> list[str]:
    normalized, errors = load_normalized_geometry_ids(normalized_dir)
    features, feature_errors = load_geojson_features(geojson_dir)
    errors.extend(feature_errors)

    missing = sorted(set(normalized) - set(features))
    extras = sorted(set(features) - set(normalized))
    if missing:
        errors.append(
            "Normalized geometry_id values missing from GeoJSON: "
            + ", ".join(missing)
        )
    if extras:
        errors.append(
            "GeoJSON geometry_id values missing from normalized data: "
            + ", ".join(extras)
        )

    for geometry_id in sorted(set(normalized) & set(features)):
        if normalized[geometry_id] != features[geometry_id]:
            errors.append(
                f"geometry_id '{geometry_id}' record_id mismatch: normalized "
                f"'{normalized[geometry_id]}' vs GeoJSON '{features[geometry_id]}'"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--normalized-dir", type=Path, default=Path("data/normalized")
    )
    parser.add_argument(
        "--geojson-dir", type=Path, default=Path("data/geojson")
    )
    args = parser.parse_args()

    errors = validate_join(args.normalized_dir, args.geojson_dir)
    if errors:
        print("GeoJSON validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("GeoJSON validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
