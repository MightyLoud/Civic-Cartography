from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _failures(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for target in data.get("targets", []):
        target_id = target.get("target_id", "<unknown>")
        enrichment_status = target.get("enrichment_status")
        if enrichment_status != "complete":
            reasons = target.get("enrichment_reasons") or []
            reason_text = "; ".join(str(reason) for reason in reasons) or "no enrichment reason recorded"
            failures.append(
                f"{target_id}: enrichment_status={enrichment_status!r}; {reason_text}"
            )
        for attempt in target.get("attempts", []):
            if attempt.get("error") == "No validation match found":
                failures.append(
                    f"{target_id}: selector {attempt.get('ocdid', '<unknown>')} used stub generation after zero validation matches"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed when production diagnostics contain partial enrichment or zero-match stub generation."
    )
    parser.add_argument("diagnostics", nargs="+", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    for path in args.diagnostics:
        failures.extend(f"{path}: {failure}" for failure in _failures(path))

    if failures:
        print("production enrichment guard: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"production enrichment guard: PASS ({len(args.diagnostics)} diagnostics file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
