from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from civic_cartography.authoritative_overrides import (
    AuthoritativeOverride,
    load_authoritative_overrides,
    resolve_authoritative_override,
)

import capture_upstream_fixtures as base_capture


def _candidate_with_override(
    api: dict[str, Any], override: AuthoritativeOverride
) -> Any:
    ingest = base_capture._make_ingest(
        api, override.ocdid, override.canonical_name
    )
    ingest.raw_record["_jurisdiction_override"] = override.generator_override
    ingest.raw_record["_source_override"] = override.source_override
    ingest.raw_record["_authoritative_override_id"] = override.override_id
    ingest.raw_record["_verified_asof"] = override.verified_asof
    return base_capture.Candidate(
        override.ocdid,
        override.canonical_name,
        "authoritative_override",
        ingest,
    )


def install_authoritative_overrides(
    overrides: tuple[AuthoritativeOverride, ...],
) -> None:
    original_candidate_index = base_capture._candidate_index
    original_resolve_target = base_capture._resolve_target

    def candidate_index(api: dict[str, Any], match_results: Any) -> dict[str, Any]:
        candidates = original_candidate_index(api, match_results)
        for override in overrides:
            candidates[override.ocdid] = _candidate_with_override(api, override)
        return candidates

    def resolve_target(
        target: dict[str, Any], candidates: dict[str, Any]
    ) -> tuple[list[Any], str, str | None]:
        selector = target.get("selector")
        if isinstance(selector, dict) and selector.get("type") == "explicit_lookup":
            override = resolve_authoritative_override(
                overrides,
                state=str(target.get("state", "")),
                name=str(selector.get("name", "")),
            )
            if override is not None:
                candidate = candidates.get(override.ocdid)
                if candidate is None:
                    return (
                        [],
                        "not_found",
                        f"Authoritative override {override.override_id} was not injected.",
                    )
                return (
                    [candidate],
                    "matched",
                    f"Resolved by authoritative override {override.override_id}.",
                )
        return original_resolve_target(target, candidates)

    base_capture._candidate_index = candidate_index
    base_capture._resolve_target = resolve_target


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--override-registry", required=True)
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> int:
    args, remaining = parse_args(argv)
    overrides = load_authoritative_overrides(Path(args.override_registry))
    install_authoritative_overrides(overrides)
    return base_capture.main(remaining)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
