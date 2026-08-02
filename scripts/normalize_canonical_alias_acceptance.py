from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml

from civic_cartography.canonical_aliases import (
    CanonicalAlias,
    CanonicalAliasError,
    load_canonical_aliases,
    resolve_canonical_alias,
)


class CanonicalAliasAcceptanceError(ValueError):
    """Raised when maintained alias evidence cannot be evaluated safely."""


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalAliasAcceptanceError(f"{location} must be a mapping")
    return dict(value)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CanonicalAliasAcceptanceError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CanonicalAliasAcceptanceError(f"{label} is invalid JSON: {path}") from exc
    return _require_mapping(raw, label)


def _load_manifest_targets(path: Path) -> dict[str, dict[str, Any]]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CanonicalAliasAcceptanceError(f"target manifest not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise CanonicalAliasAcceptanceError(
            f"target manifest is invalid YAML: {path}"
        ) from exc
    root = _require_mapping(raw, "target_manifest")
    raw_targets = root.get("targets")
    if not isinstance(raw_targets, list):
        raise CanonicalAliasAcceptanceError("target_manifest.targets must be a list")
    targets: dict[str, dict[str, Any]] = {}
    for index, raw_target in enumerate(raw_targets):
        target = _require_mapping(raw_target, f"target_manifest.targets[{index}]")
        target_id = target.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise CanonicalAliasAcceptanceError(
                f"target_manifest.targets[{index}].target_id must be a string"
            )
        targets[target_id] = target
    return targets


def _alias_for_target(
    aliases: tuple[CanonicalAlias, ...], target: Mapping[str, Any]
) -> CanonicalAlias | None:
    selector = target.get("selector")
    if not isinstance(selector, dict):
        return None
    if selector.get("type") != "alias_group":
        return None
    if selector.get("canonical_rule") != "maintained_alias":
        return None
    members = selector.get("members")
    if not isinstance(members, list):
        return None
    return resolve_canonical_alias(
        aliases,
        state=str(target.get("state", "")),
        members=members,
    )


def _alias_invariant_errors(
    alias: CanonicalAlias,
    attempts: list[dict[str, Any]],
    overlay: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    by_ocdid = {str(attempt.get("ocdid", "")): attempt for attempt in attempts}
    if set(by_ocdid) != set(alias.members):
        errors.append(
            "attempt member set does not match maintained alias members: "
            f"expected={sorted(alias.members)}, actual={sorted(by_ocdid)}"
        )
        return errors

    canonical_attempts = [
        attempt
        for attempt in attempts
        if attempt.get("canonical_alias_is_canonical") is True
    ]
    if len(canonical_attempts) != 1:
        errors.append(
            f"expected exactly one canonical attempt; found {len(canonical_attempts)}"
        )
    elif canonical_attempts[0].get("ocdid") != alias.canonical_member:
        errors.append("canonical attempt does not match maintained canonical member")

    expected_jurisdiction = alias.canonical_jurisdiction_ocdid
    for member in alias.members:
        attempt = by_ocdid[member]
        if not attempt.get("division_path"):
            errors.append(f"alias member {member} is missing its Division artifact")
        if attempt.get("canonical_alias_id") != alias.alias_id:
            errors.append(f"alias member {member} is missing canonical alias identity")
        if attempt.get("canonical_jurisdiction_ocdid") != expected_jurisdiction:
            errors.append(
                f"alias member {member} does not reference the canonical Jurisdiction"
            )
        if member == alias.canonical_member:
            if not attempt.get("jurisdiction_path"):
                errors.append("canonical member is missing its Jurisdiction artifact")
            if attempt.get("suppress_jurisdiction_generation") is not False:
                errors.append("canonical member must not suppress Jurisdiction generation")
        else:
            if attempt.get("jurisdiction_path"):
                errors.append(
                    f"secondary alias member {member} generated a duplicate Jurisdiction"
                )
            if attempt.get("suppress_jurisdiction_generation") is not True:
                errors.append(
                    f"secondary alias member {member} was not explicitly suppressed"
                )

    resolved = overlay.get("resolved_ocdids")
    if not isinstance(resolved, list) or set(resolved) != set(alias.members):
        errors.append("execution overlay does not resolve the full alias member set")
    division_paths = overlay.get("division_paths")
    if not isinstance(division_paths, list) or len(set(division_paths)) != len(
        alias.members
    ):
        errors.append("execution overlay must contain one Division path per alias member")
    jurisdiction_paths = overlay.get("jurisdiction_paths")
    if not isinstance(jurisdiction_paths, list) or len(set(jurisdiction_paths)) != 1:
        errors.append("execution overlay must contain exactly one Jurisdiction path")
    if overlay.get("inferred_classification") != alias.classification:
        errors.append("canonical Jurisdiction classification does not match the registry")
    if overlay.get("classification_status") != "matched":
        errors.append("canonical Jurisdiction classification did not match the manifest")
    return errors


def normalize_canonical_alias_acceptance(
    aliases: tuple[CanonicalAlias, ...],
    manifest_targets: Mapping[str, Mapping[str, Any]],
    execution_results: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    execution = copy.deepcopy(_require_mapping(execution_results, "execution_results"))
    diagnostic_root = copy.deepcopy(_require_mapping(diagnostics, "diagnostics"))
    if execution.get("version") != 1:
        raise CanonicalAliasAcceptanceError("execution_results.version must be 1")
    results = _require_mapping(execution.get("results"), "execution_results.results")
    raw_details = diagnostic_root.get("targets")
    if not isinstance(raw_details, list):
        raise CanonicalAliasAcceptanceError("diagnostics.targets must be a list")

    details: list[dict[str, Any]] = []
    detail_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_detail in enumerate(raw_details):
        detail = _require_mapping(raw_detail, f"diagnostics.targets[{index}]")
        target_id = detail.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise CanonicalAliasAcceptanceError(
                f"diagnostics.targets[{index}].target_id must be a string"
            )
        details.append(detail)
        detail_by_id[target_id] = detail

    evaluated: list[str] = []
    for target_id, target in manifest_targets.items():
        alias = _alias_for_target(aliases, target)
        if alias is None:
            continue
        raw_overlay = results.get(target_id)
        detail = detail_by_id.get(target_id)
        if not isinstance(raw_overlay, dict) or detail is None:
            raise CanonicalAliasAcceptanceError(
                f"canonical alias target {target_id} requires execution and diagnostics"
            )
        overlay = dict(raw_overlay)
        raw_attempts = detail.get("attempts")
        if not isinstance(raw_attempts, list):
            raise CanonicalAliasAcceptanceError(
                f"canonical alias target {target_id} attempts must be a list"
            )
        attempts = [
            _require_mapping(item, f"diagnostics.{target_id}.attempts[{index}]")
            for index, item in enumerate(raw_attempts)
        ]
        errors = _alias_invariant_errors(alias, attempts, overlay)
        detail["canonical_alias"] = {
            "alias_id": alias.alias_id,
            "members": list(alias.members),
            "canonical_member": alias.canonical_member,
            "canonical_jurisdiction_ocdid": alias.canonical_jurisdiction_ocdid,
            "invariant_errors": errors,
        }
        if errors:
            overlay["exception_class"] = "upstream_alias_noncanonical"
            overlay["review_reason"] = " | ".join(errors)
        else:
            overlay["generation_status"] = "generated"
            overlay["exception_class"] = None
            overlay["review_reason"] = None
        detail["overlay"] = copy.deepcopy(overlay)
        results[target_id] = overlay
        evaluated.append(target_id)

    execution["results"] = results
    diagnostic_root["targets"] = details
    diagnostic_root["canonical_alias_semantics"] = {
        "version": 1,
        "evaluated_targets": sorted(evaluated),
        "rule": (
            "every maintained alias member must produce a Division; exactly one "
            "canonical member produces the shared Jurisdiction; secondary members "
            "must explicitly reference it and suppress duplicate generation"
        ),
    }
    return execution, diagnostic_root


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize maintained canonical alias acceptance evidence."
    )
    parser.add_argument("--alias-registry", required=True)
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--execution-results", required=True)
    parser.add_argument("--diagnostics", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    execution_path = Path(args.execution_results)
    diagnostics_path = Path(args.diagnostics)
    try:
        execution, diagnostics = normalize_canonical_alias_acceptance(
            load_canonical_aliases(Path(args.alias_registry)),
            _load_manifest_targets(Path(args.target_manifest)),
            _load_json(execution_path, "execution_results"),
            _load_json(diagnostics_path, "diagnostics"),
        )
        _write_json(execution_path, execution)
        _write_json(diagnostics_path, diagnostics)
    except (
        CanonicalAliasAcceptanceError,
        CanonicalAliasError,
        OSError,
    ) as exc:
        print(f"canonical-alias acceptance error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
