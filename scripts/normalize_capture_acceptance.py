from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml


class AcceptanceSemanticsError(ValueError):
    """Raised when capture evidence cannot be normalized safely."""


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AcceptanceSemanticsError(f"{location} must be a mapping")
    return dict(value)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AcceptanceSemanticsError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceSemanticsError(f"{label} is invalid JSON: {path}") from exc
    return _require_mapping(raw, label)


def _load_targets(path: Path) -> dict[str, dict[str, Any]]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AcceptanceSemanticsError(f"target manifest not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise AcceptanceSemanticsError(f"target manifest is invalid YAML: {path}") from exc

    root = _require_mapping(raw, "target_manifest")
    raw_targets = root.get("targets")
    if not isinstance(raw_targets, list):
        raise AcceptanceSemanticsError("target_manifest.targets must be a list")

    targets: dict[str, dict[str, Any]] = {}
    for index, raw_target in enumerate(raw_targets):
        target = _require_mapping(raw_target, f"target_manifest.targets[{index}]")
        target_id = target.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise AcceptanceSemanticsError(
                f"target_manifest.targets[{index}].target_id must be a string"
            )
        targets[target_id] = target
    return targets


def _enrichment_status(attempts: list[dict[str, Any]]) -> str:
    if not attempts:
        return "not_run"
    statuses = [attempt.get("status") for attempt in attempts]
    if all(status == "success" for status in statuses):
        return "complete"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "partial"


def _enrichment_reasons(attempts: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for attempt in attempts:
        status = attempt.get("status")
        if status == "success":
            continue
        ocdid = attempt.get("ocdid") or "unknown"
        reason = f"{ocdid}: status={status or 'unknown'}"
        error = attempt.get("error")
        if error:
            reason += f"; error={error}"
        reasons.append(reason)
    return reasons


def _artifacts_complete(attempts: list[dict[str, Any]]) -> bool:
    return bool(attempts) and all(
        attempt.get("division_path") and attempt.get("jurisdiction_path")
        for attempt in attempts
    )


def normalize_capture_semantics(
    manifest_targets: Mapping[str, Mapping[str, Any]],
    execution_results: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate artifact generation from upstream enrichment status.

    A target is generated when every selected upstream candidate produced both a
    Division and Jurisdiction artifact. Upstream partial status remains visible
    in diagnostics as enrichment metadata instead of being misreported as
    partial generation.
    """

    execution = copy.deepcopy(_require_mapping(execution_results, "execution_results"))
    diagnostic_root = copy.deepcopy(_require_mapping(diagnostics, "diagnostics"))

    if execution.get("version") != 1:
        raise AcceptanceSemanticsError("execution_results.version must be 1")
    results = _require_mapping(execution.get("results"), "execution_results.results")
    raw_diagnostics = diagnostic_root.get("targets")
    if not isinstance(raw_diagnostics, list):
        raise AcceptanceSemanticsError("diagnostics.targets must be a list")

    diagnostic_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_detail in enumerate(raw_diagnostics):
        detail = _require_mapping(raw_detail, f"diagnostics.targets[{index}]")
        target_id = detail.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise AcceptanceSemanticsError(
                f"diagnostics.targets[{index}].target_id must be a string"
            )
        diagnostic_by_id[target_id] = detail

    for target_id, raw_overlay in results.items():
        target = manifest_targets.get(target_id)
        detail = diagnostic_by_id.get(target_id)
        if target is None or detail is None:
            raise AcceptanceSemanticsError(
                f"capture target {target_id} must exist in manifest and diagnostics"
            )
        overlay = _require_mapping(
            raw_overlay, f"execution_results.results.{target_id}"
        )
        raw_attempts = detail.get("attempts")
        if not isinstance(raw_attempts, list):
            raise AcceptanceSemanticsError(
                f"diagnostics target {target_id} attempts must be a list"
            )
        attempts = [
            _require_mapping(item, f"diagnostics.{target_id}.attempts[{index}]")
            for index, item in enumerate(raw_attempts)
        ]

        enrichment_status = _enrichment_status(attempts)
        enrichment_reasons = _enrichment_reasons(attempts)
        detail["enrichment_status"] = enrichment_status
        detail["enrichment_reasons"] = enrichment_reasons

        if overlay.get("match_status") != "matched" or not _artifacts_complete(attempts):
            results[target_id] = overlay
            continue

        overlay["generation_status"] = "generated"
        selector = target.get("selector")
        selector_type = selector.get("type") if isinstance(selector, dict) else None

        if enrichment_status == "failed":
            overlay["exception_class"] = "upstream_enrichment_failed"
            overlay["review_reason"] = " | ".join(enrichment_reasons)
        elif selector_type == "alias_group" and len(
            overlay.get("jurisdiction_paths") or []
        ) != 1:
            overlay["exception_class"] = "upstream_alias_noncanonical"
            overlay["review_reason"] = (
                "Alias group generated multiple Jurisdiction artifacts; one "
                "canonical Jurisdiction is required."
            )
        elif overlay.get("classification_status") == "matched":
            overlay["exception_class"] = None
            overlay["review_reason"] = None
        else:
            overlay["exception_class"] = "upstream_classification_mismatch"
            overlay["review_reason"] = (
                "Generated artifacts did not match the manifest classification."
            )

        detail["overlay"] = copy.deepcopy(overlay)
        results[target_id] = overlay

    execution["results"] = results
    diagnostic_root["targets"] = raw_diagnostics
    diagnostic_root["acceptance_semantics"] = {
        "version": 1,
        "generation_rule": (
            "generated when every selected candidate has Division and "
            "Jurisdiction artifact paths"
        ),
        "enrichment_rule": (
            "upstream response status is recorded separately and partial "
            "enrichment does not negate complete artifact generation"
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
        description="Normalize upstream capture generation and enrichment semantics."
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--execution-results", required=True)
    parser.add_argument("--diagnostics", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.target_manifest)
    execution_path = Path(args.execution_results)
    diagnostics_path = Path(args.diagnostics)
    try:
        execution, diagnostics = normalize_capture_semantics(
            _load_targets(manifest_path),
            _load_json(execution_path, "execution_results"),
            _load_json(diagnostics_path, "diagnostics"),
        )
        _write_json(execution_path, execution)
        _write_json(diagnostics_path, diagnostics)
    except (AcceptanceSemanticsError, OSError) as exc:
        print(f"capture-semantics error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
