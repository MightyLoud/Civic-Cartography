from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from civic_cartography.production_wave import (
    ProductionWaveError,
    select_production_wave,
    write_wave_manifest,
)
from civic_cartography.target_manifest import ManifestError, load_manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select one fixed production wave from a batch manifest."
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--expected-target-count", type=int, default=20)
    parser.add_argument("--result-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        wave_manifest = select_production_wave(
            load_manifest(args.target_manifest),
            args.wave,
            expected_target_count=args.expected_target_count,
        )
        write_wave_manifest(wave_manifest, args.result_path)
    except (ManifestError, ProductionWaveError, OSError, ValueError) as exc:
        print(f"production-wave-selection error: {exc}", file=sys.stderr)
        return 2
    print(
        f"Wrote {len(wave_manifest.targets)} targets for {args.wave} "
        f"to {args.result_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
