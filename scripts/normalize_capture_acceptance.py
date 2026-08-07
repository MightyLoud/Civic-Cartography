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


MANIFEST_NAME_SOURCE = "Civic-Cartography target manifest"
MANIFEST_NAME_SOURCE_URL = "https://github.com/MightyLoud/Civic-Cartography"


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


def _artifact_path(artifact_root: Path, raw_path: Any, location: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise AcceptanceSemanticsError(f"{location} must be a non-empty relative path")
    relative = Path(raw_path.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise AcceptanceSemanticsError(f"{location} must stay inside artifact_root")
    root = artifact_root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AcceptanceSemanticsError(f"{location} escapes artifact_root") from exc
    return resolved


def _normalize_name_sourcing(raw: dict[str, Any]) -> None:
    sourcing = raw.get("sourcing")
    if sourcing is None:
        sourcing = []
    if not isinstance(sourcing, list):
        raise AcceptanceSemanticsError("Jurisdiction sourcing must be a list")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(sourcing):
        source = _require_mapping(item, f"Jurisdiction sourcing[{index}]")
        fields = source.get("field")
        if isinstance(fields, list) and "name" in fields:
            source["field"] = [field for field in fields if field != "name"]
            if not source["field"]:
                continue
        normalized.append(source)

    normalized.append(
        {
            "field": ["name"],
            "source_name": MANIFEST_NAME_SOURCE,
            "source_type": "human_researched",
            "source_url": {"repository": MANIFEST_NAME_SOURCE_URL},
            "source_description": (
                "Human-facing Jurisdiction name supplied by the frozen "
                "Civic-Cartography target manifest."
            ),
        }
    )
    raw["sourcing"] = normalized


def _normalize_jurisdiction_names(
    manifest_targets: Mapping[str, Mapping[str, Any]],
    results: Mapping[str, Any],
    diagnostic_by_id: Mapping[str, dict[str, Any]],
    artifact_root: Path,
) -> list[str]:
    normalized_targets: list[str] = []
    for target_id, raw_overlay in results.items():
        target = manifest_targets.get(target_id)
        detail = diagnostic_by_id.get(target_id)
        if target is None or detail is None or not isinstance(raw_overlay, dict):
            continue

        expected_name = target.get("jurisdiction_name")
        if not isinstance(expected_name, str) or not expected_name.strip():
            raise AcceptanceSemanticsError(
                f"target_manifest target {target_id} jurisdiction_name must be a string"
            )
        expected_name = expected_name.strip()

        paths = raw_overlay.get("jurisdiction_paths")
        if not isinstance(paths, list) or not paths:
            continue

        path_details: list[dict[str, Any]] = []
        for index, raw_path in enumerate(paths):
            path = _artifact_path(
                artifact_root,
                raw_path,
                f"execution_results.results.{target_id}.jurisdiction_paths[{index}]",
            )
            if not path.is_file():
                raise AcceptanceSemanticsError(
                    f"Jurisdiction artifact for {target_id} not found: {raw_path}"
                )
            try:
                artifact = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                raise AcceptanceSemanticsError(
                    f"Jurisdiction artifact for {target_id} is invalid YAML: {raw_path}"
                ) from exc
            artifact = _require_mapping(artifact, f"Jurisdiction artifact {raw_path}")
            previous_name = artifact.get("name")
            changed = previous_name != expected_name
            if changed:
                artifact["name"] = expected_name
                _normalize_name_sourcing(artifact)
                path.write_text(
                    yaml.safe_dump(artifact, sort_keys=False, allow_unicode=True),
                    encoding="utf-8",
                )
            path_details.append(
                {
                    "path": raw_path,
                    "previous_name": previous_name,
                    "normalized_name": expected_name,
                    "changed": changed,
                }
            )

        detail["jurisdiction_name_normalization"] = {
            "expected_name": expected_name,
            "paths": path_details,
            "changed_count": sum(1 for item in path_details if item["changed"]),
            "rule": (
                "generated Jurisdiction artifacts retain the manifest jurisdiction_name; "
                "OCDID and classification are unchanged"
            ),
        }
        normalized_targets.append(target_id)
    return normalized_targets


def normalize_capture_semantics(
    manifest_targets: Mapping[str, Mapping[str, Any]],
    execution_results: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
    artifact_root: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate artifact generation from enrichment and normalize display names.

    A target is generated when every selected upstream candidate produced both a
    Division and Jurisdiction artifact. Upstream partial status remains visible
    in diagnostics as enrichment metadata instead of being misreported as
    partial generation. When an artifact root is supplied, each generated
    Jurisdiction's human-facing ``name`` is normalized to the frozen manifest's
    ``jurisdiction_name`` after classification/generation have already run.
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
    normalized_diagnostics: list[dict[str, Any]] = []
    for index, raw_detail in enumerate(raw_diagnostics):
        detail = _require_mapping(raw_detail, f"diagnostics.targets[{index}]")
        target_id = detail.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise AcceptanceSemanticsError(
                f"diagnostics.targets[{index}].target_id must be a string"
            )
        diagnostic_by_id[target_id] = detail
        normalized_diagnostics.append(detail)

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
            detail["overlay"] = copy.deepcopy(overlay)
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

    normalized_names: list[str] = []
    if artifact_root is not None:
        normalized_names = _normalize_jurisdiction_names(
            manifest_targets,
            results,
            diagnostic_by_id,
            Path(artifact_root),
        )

    execution["results"] = results
    diagnostic_root["targets"] = normalized_diagnostics
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
        "jurisdiction_name_rule": (
            "after generation/classification, generated Jurisdiction names are "
            "normalized to the frozen manifest jurisdiction_name without changing "
            "OCDID or classification"
        ),
        "jurisdiction_name_targets": sorted(normalized_names),
    }
    return execution, diagnostic_root


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize upstream capture generation, enrichment, and display names."
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
            artifact_root=execution_path.parent / "artifacts",
        )
        _write_json(execution_path, execution)
        _write_json(diagnostics_path, diagnostics)
    except (AcceptanceSemanticsError, OSError) as exc:
        print(f"capture-semantics error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
