from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.fixture_harness import FixtureHarnessError
from civic_cartography.production_wave import (
    ProductionWaveError,
    run_production_wave_acceptance,
)
from civic_cartography.target_manifest import ManifestError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a fixed production wave across two clean captures."
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--first-report", required=True)
    parser.add_argument("--second-report", required=True)
    parser.add_argument("--selection-crosswalk", required=True)
    parser.add_argument("--upstream-repository", required=True)
    parser.add_argument("--upstream-revision", required=True)
    parser.add_argument("--expected-target-count", type=int, default=20)
    parser.add_argument("--target-only-patch-count", type=int, default=0)
    parser.add_argument("--result-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_production_wave_acceptance(
            manifest_path=args.target_manifest,
            first_report_path=args.first_report,
            second_report_path=args.second_report,
            crosswalk_path=args.selection_crosswalk,
            result_path=args.result_path,
            upstream_repository=args.upstream_repository,
            upstream_revision=args.upstream_revision,
            expected_target_count=args.expected_target_count,
            target_only_patch_count=args.target_only_patch_count,
        )
    except (
        FixtureHarnessError,
        ManifestError,
        ProductionWaveError,
        OSError,
        ValueError,
    ) as exc:
        print(f"production-wave-acceptance error: {exc}", file=sys.stderr)
        return 2
    return 0 if report["summary"]["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
