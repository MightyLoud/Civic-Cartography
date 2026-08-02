from __future__ import annotations

import argparse
import sys

from civic_cartography.batch_acceptance import (
    BatchAcceptanceError,
    run_batch_acceptance,
)
from civic_cartography.fixture_harness import FixtureHarnessError
from civic_cartography.target_manifest import ManifestError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the complete Batch Pilot 25 acceptance criteria."
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--first-report", required=True)
    parser.add_argument("--second-report", required=True)
    parser.add_argument("--upstream-repository", required=True)
    parser.add_argument("--upstream-revision", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument("--target-only-patch-count", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_batch_acceptance(
            manifest_path=args.target_manifest,
            first_report_path=args.first_report,
            second_report_path=args.second_report,
            result_path=args.result_path,
            upstream_repository=args.upstream_repository,
            upstream_revision=args.upstream_revision,
            target_only_patch_count=args.target_only_patch_count,
        )
    except (
        BatchAcceptanceError,
        FixtureHarnessError,
        ManifestError,
        OSError,
        ValueError,
    ) as exc:
        print(f"batch-acceptance error: {exc}", file=sys.stderr)
        return 2

    return 0 if report["summary"]["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
