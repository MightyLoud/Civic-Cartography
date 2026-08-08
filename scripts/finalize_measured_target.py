from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.completion_manifest import (
    CompletionManifestError,
    run_completion_manifest,
)
from civic_cartography.completion_register import (
    CompletionRegisterError,
    upsert_completion_register,
)
from civic_cartography.fixture_harness import FixtureHarnessError
from civic_cartography.target_manifest import ManifestError


class MeasuredTargetFinalizerError(ValueError):
    """Raised when one measured target cannot be finalized safely."""


def finalize_measured_target(
    *,
    manifest_path: str | Path,
    first_report_path: str | Path,
    second_report_path: str | Path,
    source_manifest_path: str | Path,
    completion_manifest_path: str | Path,
    register_path: str | Path,
    evidence_ref: str,
) -> dict[str, Any]:
    """Evaluate one measured target and register it only after COMPLETE_OK.

    The completion manifest is always written so failed runs retain auditable
    gate evidence. The stable register is mutated only when the manifest
    contains exactly one target and that target satisfies every completion gate.
    """
    completion = run_completion_manifest(
        manifest_path=manifest_path,
        first_report_path=first_report_path,
        second_report_path=second_report_path,
        source_manifest_path=source_manifest_path,
        result_path=completion_manifest_path,
    )
    targets = completion.get("targets")
    if not isinstance(targets, list) or len(targets) != 1:
        raise MeasuredTargetFinalizerError(
            "measured target finalizer requires exactly one target"
        )

    target = targets[0]
    if not target.get("complete_ok"):
        failed_gates = target.get("failed_gates") or []
        raise MeasuredTargetFinalizerError(
            f"{target.get('target_id', 'target')} is not COMPLETE; "
            f"failed_gates={failed_gates}"
        )

    rows = upsert_completion_register(
        completion,
        register_path=register_path,
        evidence_ref=evidence_ref,
    )
    return {
        "target_id": target["target_id"],
        "evaluation_id": completion["evaluation_id"],
        "complete_ok": True,
        "register_row_count": len(rows),
        "evidence_ref": evidence_ref,
        "completion_manifest_path": str(completion_manifest_path),
        "register_path": str(register_path),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize one measured target: emit explicit completion gates and "
            "upsert the stable register only when COMPLETE_OK is true."
        )
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--first-report", required=True)
    parser.add_argument("--second-report", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--completion-manifest", required=True)
    parser.add_argument(
        "--register-path",
        default="evidence/measured-batch-100/completion-register.csv",
    )
    parser.add_argument("--evidence-ref", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = finalize_measured_target(
            manifest_path=args.target_manifest,
            first_report_path=args.first_report,
            second_report_path=args.second_report,
            source_manifest_path=args.source_manifest,
            completion_manifest_path=args.completion_manifest,
            register_path=args.register_path,
            evidence_ref=args.evidence_ref,
        )
    except (
        CompletionManifestError,
        CompletionRegisterError,
        FixtureHarnessError,
        ManifestError,
        MeasuredTargetFinalizerError,
        OSError,
        ValueError,
    ) as exc:
        print(f"measured-target-finalizer error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Finalized {result['target_id']} COMPLETE "
        f"(evaluation_id={result['evaluation_id']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
