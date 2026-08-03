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
from civic_cartography.canonical_aliases import (
    CanonicalAlias,
    load_canonical_aliases,
    resolve_canonical_alias,
)

import capture_upstream_fixtures as base_capture


def _candidate_with_override(
    api: dict[str, Any], override: AuthoritativeOverride
) -> Any:
    ingest = base_capture._make_ingest(api, override.ocdid, override.canonical_name)
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


def _candidate_with_canonical_alias(candidate: Any, alias: CanonicalAlias) -> Any:
    raw_record = candidate.ingest.raw_record
    if not isinstance(raw_record, dict):
        raise ValueError(
            f"candidate {candidate.ocdid} raw_record must be a mapping for alias metadata"
        )
    metadata = alias.member_metadata(candidate.ocdid)
    raw_record.update(metadata)
    member_display_name = metadata.get("_canonical_alias_member_display_name")
    if isinstance(member_display_name, str):
        raw_record["name"] = member_display_name
    raw_record["_canonical_alias_verified_asof"] = alias.verified_asof
    if candidate.ocdid == alias.canonical_member:
        raw_record["_jurisdiction_override"] = alias.generator_override
        raw_record["_source_override"] = alias.source_override
    return candidate


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


def install_canonical_aliases(aliases: tuple[CanonicalAlias, ...]) -> None:
    original_resolve_target = base_capture._resolve_target
    original_capture_target = base_capture._capture_target

    def resolve_target(
        target: dict[str, Any], candidates: dict[str, Any]
    ) -> tuple[list[Any], str, str | None]:
        selector = target.get("selector")
        if (
            isinstance(selector, dict)
            and selector.get("type") == "alias_group"
            and selector.get("canonical_rule") == "maintained_alias"
        ):
            members = selector.get("members")
            if isinstance(members, list):
                alias = resolve_canonical_alias(
                    aliases,
                    state=str(target.get("state", "")),
                    members=members,
                )
                if alias is not None:
                    missing = sorted(member for member in alias.members if member not in candidates)
                    if missing:
                        return (
                            [],
                            "alias_group_pending",
                            f"Maintained alias {alias.alias_id} is missing members: {missing}",
                        )
                    ordered_members = [
                        alias.canonical_member,
                        *sorted(
                            member
                            for member in alias.members
                            if member != alias.canonical_member
                        ),
                    ]
                    selected = [
                        _candidate_with_canonical_alias(candidates[member], alias)
                        for member in ordered_members
                    ]
                    return (
                        selected,
                        "matched",
                        f"Resolved by maintained canonical alias {alias.alias_id}.",
                    )
        return original_resolve_target(target, candidates)

    async def capture_target(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        selected = args[2] if len(args) > 2 else kwargs.get("selected", [])
        overlay, diagnostics = await original_capture_target(*args, **kwargs)
        attempts = diagnostics.get("attempts") if isinstance(diagnostics, dict) else None
        if isinstance(attempts, list):
            for attempt, candidate in zip(attempts, selected, strict=True):
                raw_record = getattr(candidate.ingest, "raw_record", {})
                if not isinstance(raw_record, dict):
                    continue
                for key in (
                    "_canonical_alias_id",
                    "_canonical_alias_is_canonical",
                    "_canonical_alias_member",
                    "_canonical_division_ocdid",
                    "_canonical_jurisdiction_ocdid",
                    "_suppress_jurisdiction_generation",
                    "_canonical_alias_verified_asof",
                    "_canonical_alias_member_display_name",
                ):
                    if key in raw_record:
                        attempt[key.removeprefix("_")] = raw_record[key]
        return overlay, diagnostics

    base_capture._resolve_target = resolve_target
    base_capture._capture_target = capture_target


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--override-registry", required=True)
    parser.add_argument("--alias-registry")
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> int:
    args, remaining = parse_args(argv)
    overrides = load_authoritative_overrides(Path(args.override_registry))
    install_authoritative_overrides(overrides)
    if args.alias_registry:
        aliases = load_canonical_aliases(Path(args.alias_registry))
        install_canonical_aliases(aliases)
    return base_capture.main(remaining)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
