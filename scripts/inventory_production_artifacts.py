from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.fixture_harness import FixtureHarnessError, load_result_report
from civic_cartography.production_wave import (
    ProductionWaveError,
    build_artifact_inventory,
    write_artifact_inventory,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hash every target and shared artifact in a production run."
    )
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--result-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        inventory = build_artifact_inventory(
            args.artifact_root, load_result_report(args.report)
        )
        write_artifact_inventory(inventory, args.result_path)
    except (FixtureHarnessError, ProductionWaveError, OSError, ValueError) as exc:
        print(f"production-artifact-inventory error: {exc}", file=sys.stderr)
        return 2
    print(
        f"Hashed {inventory['file_count']} artifacts "
        f"({inventory['target_artifact_count']} target, "
        f"{inventory['shared_artifact_count']} shared)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
