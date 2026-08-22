#!/usr/bin/env python3
"""Compare Schleicher derivation contracts while isolating renderer diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

RENDER_DIAGNOSTIC_KEYS = {
    "mean_color_distance",
    "minimum_color_separation",
}
EXPECTED_DIAGNOSTIC_COUNT = 8


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_render_diagnostics(
    value: Any, path: str = "$"
) -> list[tuple[str, str, float]]:
    diagnostics: list[tuple[str, str, float]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key in RENDER_DIAGNOSTIC_KEYS:
                if isinstance(item, bool) or not isinstance(item, (int, float)):
                    raise SystemExit(f"{item_path} must be numeric, found {item!r}")
                numeric = float(item)
                if not math.isfinite(numeric) or numeric < 0:
                    raise SystemExit(
                        f"{item_path}={numeric} must be finite and nonnegative"
                    )
                diagnostics.append((item_path, key, numeric))
            else:
                diagnostics.extend(collect_render_diagnostics(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            diagnostics.extend(
                collect_render_diagnostics(item, f"{path}[{index}]")
            )
    return diagnostics


def without_render_diagnostics(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: without_render_diagnostics(item)
            for key, item in value.items()
            if key not in RENDER_DIAGNOSTIC_KEYS
        }
    if isinstance(value, list):
        return [without_render_diagnostics(item) for item in value]
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


def compare_contracts(committed: Any, fresh: Any) -> None:
    committed_diagnostics = collect_render_diagnostics(committed)
    fresh_diagnostics = collect_render_diagnostics(fresh)
    if len(committed_diagnostics) != EXPECTED_DIAGNOSTIC_COUNT:
        raise SystemExit(
            f"Committed Schleicher contract has {len(committed_diagnostics)} "
            f"renderer diagnostics; expected {EXPECTED_DIAGNOSTIC_COUNT}"
        )
    if len(fresh_diagnostics) != EXPECTED_DIAGNOSTIC_COUNT:
        raise SystemExit(
            f"Fresh Schleicher contract has {len(fresh_diagnostics)} "
            f"renderer diagnostics; expected {EXPECTED_DIAGNOSTIC_COUNT}"
        )

    committed_stable = without_render_diagnostics(committed)
    fresh_stable = without_render_diagnostics(fresh)
    difference = first_difference(committed_stable, fresh_stable)
    if difference:
        raise SystemExit(f"Schleicher stable derivation contract changed: {difference}")

    changed = sum(
        committed_item[2] != fresh_item[2]
        for committed_item, fresh_item in zip(
            committed_diagnostics, fresh_diagnostics
        )
    )
    print(
        "Schleicher contract stable content exact; "
        f"{changed}/{EXPECTED_DIAGNOSTIC_COUNT} renderer diagnostic(s) changed "
        "within the controlled nonnegative range."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed-contract", type=Path, required=True)
    parser.add_argument("--fresh-contract", type=Path, required=True)
    args = parser.parse_args()

    compare_contracts(
        load_json(args.committed_contract),
        load_json(args.fresh_contract),
    )
    print(
        "Schleicher Commissioner assignments, confidence, source hashes, and "
        "contract are renderer-stable."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
