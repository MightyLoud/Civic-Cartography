from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.completion_manifest import (
    CompletionManifestError,
    run_completion_manifest,
)
from civic_cartography.fixture_harness import FixtureHarnessError
from civic_cartography.target_manifest import ManifestError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit explicit per-target civic-data completion gates."
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--first-report", required=True)
    parser.add_argument("--second-report", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument(
        "--require-all-complete",
        action="store_true",
        help="Return non-zero unless every target satisfies COMPLETE_OK.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_completion_manifest(
            manifest_path=args.target_manifest,
            first_report_path=args.first_report,
            second_report_path=args.second_report,
            source_manifest_path=args.source_manifest,
            result_path=args.result_path,
        )
    except (
        CompletionManifestError,
        FixtureHarnessError,
        ManifestError,
        OSError,
        ValueError,
    ) as exc:
        print(f"completion-manifest error: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print(
        f"Completion manifest: {summary['complete_count']}/"
        f"{summary['target_count']} COMPLETE"
    )
    if args.require_all_complete and not summary["all_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
