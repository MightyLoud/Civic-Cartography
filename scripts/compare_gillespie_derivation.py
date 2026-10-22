#!/usr/bin/env python3
"""Compare Gillespie derivation outputs while isolating renderer-only metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MIN_ASSIGNMENT_CONFIDENCE = 0.85
RENDER_METRIC_KEYS = {
    "assignment_confidence_min",
    "assignment_confidence_mean",
}
EXPECTED_METRIC_COUNTS = {
    "raw": 8,
    "canonical": 8,
    "contract": 10,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_render_metrics(value: Any, path: str = "$") -> list[tuple[str, str, float]]:
    metrics: list[tuple[str, str, float]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key in RENDER_METRIC_KEYS:
                if isinstance(item, bool) or not isinstance(item, (int, float)):
                    raise SystemExit(f"{item_path} must be numeric, found {item!r}")
                numeric = float(item)
                if not MIN_ASSIGNMENT_CONFIDENCE <= numeric <= 1.0:
                    raise SystemExit(
                        f"{item_path}={numeric} is outside "
                        f"[{MIN_ASSIGNMENT_CONFIDENCE}, 1.0]"
                    )
                metrics.append((item_path, key, numeric))
            else:
                metrics.extend(collect_render_metrics(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            metrics.extend(collect_render_metrics(item, f"{path}[{index}]"))
    return metrics


def without_render_metrics(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: without_render_metrics(item)
            for key, item in value.items()
            if key not in RENDER_METRIC_KEYS
        }
    if isinstance(value, list):
        return [without_render_metrics(item) for item in value]
    return value


def first_difference(committed: Any, fresh: Any, path: str = "$") -> str | None:
    if type(committed) is not type(fresh):
        return f"{path}: type {type(committed).__name__} != {type(fresh).__name__}"
    if isinstance(committed, dict):
        committed_keys = set(committed)
        fresh_keys = set(fresh)
        if committed_keys != fresh_keys:
            return (
                f"{path}: keys differ; missing={sorted(committed_keys - fresh_keys)!r}; "
                f"added={sorted(fresh_keys - committed_keys)!r}"
            )
        for key in sorted(committed):
            difference = first_difference(
                committed[key], fresh[key], f"{path}.{key}"
            )
            if difference:
                return difference
        return None
    if isinstance(committed, list):
        if len(committed) != len(fresh):
            return f"{path}: length {len(committed)} != {len(fresh)}"
        for index, (committed_item, fresh_item) in enumerate(zip(committed, fresh)):
            difference = first_difference(
                committed_item, fresh_item, f"{path}[{index}]"
            )
            if difference:
                return difference
        return None
    if committed != fresh:
        return f"{path}: {committed!r} != {fresh!r}"
    return None


def compare_documents(
    label: str,
    committed: Any,
    fresh: Any,
    *,
    expected_metric_count: int,
) -> None:
    committed_metrics = collect_render_metrics(committed)
    fresh_metrics = collect_render_metrics(fresh)
    if len(committed_metrics) != expected_metric_count:
        raise SystemExit(
            f"Committed {label} has {len(committed_metrics)} renderer metrics; "
            f"expected {expected_metric_count}"
        )
    if len(fresh_metrics) != expected_metric_count:
        raise SystemExit(
            f"Fresh {label} has {len(fresh_metrics)} renderer metrics; "
            f"expected {expected_metric_count}"
        )

    committed_stable = without_render_metrics(committed)
    fresh_stable = without_render_metrics(fresh)
    difference = first_difference(committed_stable, fresh_stable)
    if difference:
        raise SystemExit(f"Gillespie {label} stable derivation changed: {difference}")

    changed_metrics = sum(
        committed_item[2] != fresh_item[2]
        for committed_item, fresh_item in zip(committed_metrics, fresh_metrics)
    )
    print(
        f"Gillespie {label}: stable content exact; "
        f"{changed_metrics}/{expected_metric_count} renderer metric(s) changed "
        f"within the controlled confidence floor."
    )


def compare_paths(label: str, committed_path: Path, fresh_path: Path) -> None:
    compare_documents(
        label,
        load_json(committed_path),
        load_json(fresh_path),
        expected_metric_count=EXPECTED_METRIC_COUNTS[label],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed-raw", type=Path, required=True)
    parser.add_argument("--fresh-raw", type=Path, required=True)
    parser.add_argument("--committed-canonical", type=Path, required=True)
    parser.add_argument("--fresh-canonical", type=Path, required=True)
    parser.add_argument("--committed-contract", type=Path, required=True)
    parser.add_argument("--fresh-contract", type=Path, required=True)
    args = parser.parse_args()

    compare_paths("raw", args.committed_raw, args.fresh_raw)
    compare_paths("canonical", args.committed_canonical, args.fresh_canonical)
    compare_paths("contract", args.committed_contract, args.fresh_contract)
    print(
        "Gillespie Commissioner assignments, geometry, source hashes, and contract "
        "are renderer-stable."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
