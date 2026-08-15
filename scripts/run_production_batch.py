#!/usr/bin/env python3
"""Manifest-driven production-wave orchestration entrypoint.

NAT-FAC-001 intentionally keeps the proven state-specific capture/generation
adapters outside this module. This runner owns only state-neutral manifest and
wave selection so CI can stop encoding a state in its entrypoint.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from civic_cartography.production_wave import select_production_wave, write_wave_manifest
from civic_cartography.target_manifest import load_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument("--expected-target-count", type=int)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    expected = args.expected_target_count
    if expected is None:
        expected = sum(target.wave == args.wave for target in manifest.targets)
    if expected < 1:
        parser.error(f"wave {args.wave!r} has no targets")

    wave_manifest = select_production_wave(
        manifest,
        args.wave,
        expected_target_count=expected,
    )
    write_wave_manifest(wave_manifest, Path(args.result_path))
    print(
        f"Selected {len(wave_manifest.targets)} targets for {args.wave} "
        f"from {manifest.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
