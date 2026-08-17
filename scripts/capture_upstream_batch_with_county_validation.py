from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

from civic_cartography.authoritative_overrides import load_authoritative_overrides
from civic_cartography.canonical_aliases import load_canonical_aliases

import capture_upstream_batch as batch_capture
import capture_upstream_fixtures as base_capture
from capture_upstream_batch_with_overrides import parse_args
from capture_upstream_with_authoritative_overrides import (
    install_authoritative_overrides,
    install_canonical_aliases,
)

STATE_COUNTIES_GID = "1652436767"


def _is_state_county_target(target: dict) -> bool:
    return any(
        "/county:" in f"/{ocdid.rstrip('/')}"
        for ocdid in batch_capture._selector_ocdids(target)
    ) and batch_capture._target_admin1_type(target) == "state"


def main(argv: list[str] | None = None) -> int:
    registry_args, remaining = parse_args(argv)
    overrides = load_authoritative_overrides(Path(registry_args.override_registry))
    install_authoritative_overrides(overrides)
    if registry_args.alias_registry:
        aliases = load_canonical_aliases(Path(registry_args.alias_registry))
        install_canonical_aliases(aliases)

    original_capture_target = base_capture._capture_target

    async def capture_target_with_counties(
        api,
        target,
        selected,
        match_status,
        reason,
        fixed_asof,
        validation_path,
        artifact_root,
    ):
        effective_validation_path = Path(validation_path)
        if _is_state_county_target(target):
            county_path = (
                effective_validation_path.parent
                / "nested-divisions-state-counties-validation.csv"
            )
            county_url = batch_capture._validation_url_with_gid(
                api["validation_url"], STATE_COUNTIES_GID
            )
            base_capture._download_once(county_url, county_path)
            effective_validation_path = batch_capture._combine_validation_csvs(
                [Path(validation_path), county_path],
                effective_validation_path.parent
                / "nested-divisions-with-state-counties-validation.csv",
            )

        return await original_capture_target(
            api,
            target,
            selected,
            match_status,
            reason,
            fixed_asof,
            effective_validation_path,
            artifact_root,
        )

    base_capture._capture_target = capture_target_with_counties
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
