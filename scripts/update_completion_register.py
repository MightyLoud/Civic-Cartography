from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.completion_register import (
    CompletionRegisterError,
    load_completion_manifest,
    upsert_completion_register,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upsert completion-manifest target gates into a stable CSV register."
    )
    parser.add_argument("--completion-manifest", required=True)
    parser.add_argument("--register-path", required=True)
    parser.add_argument("--evidence-ref", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        rows = upsert_completion_register(
            load_completion_manifest(args.completion_manifest),
            register_path=args.register_path,
            evidence_ref=args.evidence_ref,
        )
    except (CompletionRegisterError, OSError, ValueError) as exc:
        print(f"completion-register error: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {len(rows)} completion register rows to {args.register_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
