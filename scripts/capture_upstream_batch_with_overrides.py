from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

from civic_cartography.authoritative_overrides import load_authoritative_overrides
from civic_cartography.canonical_aliases import load_canonical_aliases

import capture_upstream_batch as batch_capture
import capture_upstream_fixtures as base_capture
from capture_upstream_with_authoritative_overrides import (
    install_authoritative_overrides,
    install_canonical_aliases,
)


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--override-registry", required=True)
    parser.add_argument("--alias-registry")
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> int:
    registry_args, remaining = parse_args(argv)

    # MB100-004 is the unchanged D11 regression fixture under a new batch ID.
    # Reuse the already validated exact-name aliases from BP25-014 rather than
    # adding fuzzy matching or a new target-specific generator override.
    base_capture.EXPLICIT_NAME_ALIASES["MB100-004"] = set(
        base_capture.EXPLICIT_NAME_ALIASES["BP25-014"]
    )

    overrides = load_authoritative_overrides(Path(registry_args.override_registry))
    install_authoritative_overrides(overrides)
    if registry_args.alias_registry:
        aliases = load_canonical_aliases(Path(registry_args.alias_registry))
        install_canonical_aliases(aliases)

    args = batch_capture.parse_args(remaining)
    try:
        asyncio.run(batch_capture.capture_batch(args))
    except (
        batch_capture.BatchCaptureError,
        base_capture.CaptureError,
        httpx.HTTPError,
        OSError,
        ValueError,
    ) as exc:
        print(f"upstream-batch-capture error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
