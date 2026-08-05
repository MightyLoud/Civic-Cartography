#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.production_rollup import build_production_batch_rollup


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and enforce the Production Batch 2 roll-up."
    )
    parser.add_argument(
        "--wave-acceptance",
        action="append",
        required=True,
        help="Wave acceptance JSON path; repeat once per wave.",
    )
    parser.add_argument("--result-path", required=True)
    args = parser.parse_args()

    result = build_production_batch_rollup(
        args.wave_acceptance,
        batch_id="WA-PB02",
        expected_target_count=65,
        expected_wave_letters="ABCD",
    )
    result_path = Path(args.result_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if result["summary"]["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
