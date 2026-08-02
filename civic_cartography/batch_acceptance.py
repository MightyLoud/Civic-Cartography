from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, Mapping

from civic_cartography.fixture_harness import (
    DETERMINISTIC_FIELDS,
    PASSING_MATCH_STATUSES,
    evaluate_fixture_reports,
    load_result_report,
)
from civic_cartography.target_manifest import Target, TargetManifest, load_manifest


class BatchAcceptanceError(ValueError):
    """Raised when Batch Pilot acceptance evidence is incomplete or invalid."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _index_results(report: Mapping[str, Any], label: str) -> dict[str, dict[str, Any]]:
    raw_results = report.get("results")
    if not isinstance(raw_results, list):
        raise BatchAcceptanceError(f"{label}.results must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_result in enumerate(raw_results):
        if not isinstance(raw_result, dict):
            raise BatchAcceptanceError(f"{label}.results[{index}] must be a mapping")
        target_id = raw_result.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise BatchAcceptanceError(
                f"{label}.results[{index}].target_id must be a string"
            )
        if target_id in indexed:
            raise BatchAcceptanceError(f"{label} contains duplicate result {target_id}")
        indexed[target_id] = dict(raw_result)
    return indexed


def _is_classified(target: Target, result: Mapping[str, Any]) -> bool:
    return (
        result.get("match_status") in PASSING_MATCH_STATUSES
        and result.get("inferred_classification") == target.expected_classification
        and result.get("classification_status") == "matched"
    )


def _is_generated(result: Mapping[str, Any]) -> bool:
    division_paths = result.get("division_paths")
    jurisdiction_paths = result.get("jurisdiction_paths")
    hashes = result.get("output_hashes")
    expected_paths = {
        str(path)
        for path in [
            *(division_paths if isinstance(division_paths, list) else []),
            *(jurisdiction_paths if isinstance(jurisdiction_paths, list) else []),
        ]
    }
    return (
        result.get("generation_status") == "generated"
        and isinstance(division_paths, list)
        and bool(division_paths)
        and isinstance(jurisdiction_paths, list)
        and bool(jurisdiction_paths)
        and isinstance(hashes, dict)
        and bool(hashes)
        and set(hashes) == expected_paths
    )


def _requires_exception(target: Target, result: Mapping[str, Any]) -> bool:
    return not (_is_classified(target, result) and _is_generated(result))


def _exception_is_explicit(result: Mapping[str, Any]) -> bool:
    exception_class = result.get("exception_class")
    review_reason = result.get("review_reason")
    return (
        isinstance(exception_class, str)
        and bool(exception_class.strip())
        and isinstance(review_reason, str)
        and bool(review_reason.strip())
    )


def _deterministic(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    return all(first.get(field) == second.get(field) for field in DETERMINISTIC_FIELDS)


def _target_outcome(
    target: Target,
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> dict[str, Any]:
    classified = _is_classified(target, first)
    generated = _is_generated(first)
    requires_exception = _requires_exception(target, first)
    exception_explicit = (not requires_exception) or _exception_is_explicit(first)
    deterministic = _deterministic(first, second)
    return {
        "target_id": target.target_id,
        "jurisdiction_name": target.jurisdiction_name,
        "category": target.category,
        "expected_archetype": target.expected_archetype,
        "expected_classification": target.expected_classification,
        "classified_automatically": classified,
        "generated_automatically": generated,
        "deterministic": deterministic,
        "exception_required": requires_exception,
        "exception_explicit": exception_explicit,
        "match_status": first.get("match_status"),
        "inferred_classification": first.get("inferred_classification"),
        "generation_status": first.get("generation_status"),
        "exception_class": first.get("exception_class"),
        "review_reason": first.get("review_reason"),
        "human_minutes": first.get("human_minutes"),
        "resolved_ocdids": first.get("resolved_ocdids", []),
        "division_paths": first.get("division_paths", []),
        "jurisdiction_paths": first.get("jurisdiction_paths", []),
        "output_hashes": first.get("output_hashes", {}),
    }


def evaluate_batch_acceptance(
    manifest: TargetManifest,
    first_report: Mapping[str, Any],
    second_report: Mapping[str, Any],
    *,
    upstream_repository: str,
    upstream_revision: str,
    target_only_patch_count: int = 0,
) -> dict[str, Any]:
    if isinstance(target_only_patch_count, bool) or target_only_patch_count < 0:
        raise BatchAcceptanceError("target_only_patch_count must be non-negative")

    first_by_id = _index_results(first_report, "first_report")
    second_by_id = _index_results(second_report, "second_report")
    expected_ids = {target.target_id for target in manifest.targets}
    first_ids = set(first_by_id)
    second_ids = set(second_by_id)
    missing_first = sorted(expected_ids - first_ids)
    missing_second = sorted(expected_ids - second_ids)
    extra_first = sorted(first_ids - expected_ids)
    extra_second = sorted(second_ids - expected_ids)
    one_row_per_target = not (
        missing_first or missing_second or extra_first or extra_second
    )
    if not one_row_per_target:
        raise BatchAcceptanceError(
            "result rows do not match manifest targets; "
            f"missing_first={missing_first}, missing_second={missing_second}, "
            f"extra_first={extra_first}, extra_second={extra_second}"
        )

    if first_report.get("manifest_sha256") != second_report.get("manifest_sha256"):
        raise BatchAcceptanceError("report manifest hashes differ")
    if first_report.get("run_asof") != second_report.get("run_asof"):
        raise BatchAcceptanceError("report run_asof values differ")

    outcomes = [
        _target_outcome(
            target,
            first_by_id[target.target_id],
            second_by_id[target.target_id],
        )
        for target in manifest.targets
    ]
    known = [row for row in outcomes if row["category"] == "new_known_archetype"]
    discovery = [row for row in outcomes if row["category"] == "discovery"]
    if len(known) != 15:
        raise BatchAcceptanceError(
            f"Batch Pilot 25 must contain 15 known-archetype targets, found {len(known)}"
        )
    if len(discovery) != 4:
        raise BatchAcceptanceError(
            f"Batch Pilot 25 must contain 4 discovery targets, found {len(discovery)}"
        )

    known_classified_count = sum(row["classified_automatically"] for row in known)
    known_generated_count = sum(row["generated_automatically"] for row in known)
    known_classification_rate = known_classified_count / len(known)
    known_generation_rate = known_generated_count / len(known)
    deterministic_count = sum(row["deterministic"] for row in outcomes)
    exception_failures = [
        row["target_id"]
        for row in outcomes
        if row["exception_required"] and not row["exception_explicit"]
    ]

    human_minutes = [
        float(row["human_minutes"])
        for row in outcomes
        if isinstance(row["human_minutes"], (int, float))
        and not isinstance(row["human_minutes"], bool)
        and row["human_minutes"] >= 0
    ]
    human_minutes_complete = len(human_minutes) == len(outcomes)
    median_human_minutes = (
        statistics.median(human_minutes) if human_minutes_complete else None
    )

    reports_identical = _sha256_value(first_report) == _sha256_value(second_report)
    fixture_evaluation = evaluate_fixture_reports(
        manifest,
        first_report,
        second_report,
        upstream_repository=upstream_repository,
        upstream_revision=upstream_revision,
    )

    criteria = {
        "all_targets_have_one_result": one_row_per_target,
        "regression_fixtures_pass": fixture_evaluation["summary"]["gate_passed"],
        "known_classification_rate_at_least_80_percent": (
            known_classification_rate >= 0.8
        ),
        "known_generation_rate_at_least_80_percent": known_generation_rate >= 0.8,
        "all_failures_have_explicit_exception": not exception_failures,
        "second_run_is_identical": (
            deterministic_count == len(outcomes) and reports_identical
        ),
        "median_human_review_at_most_10_minutes": (
            human_minutes_complete
            and median_human_minutes is not None
            and median_human_minutes <= 10
        ),
        "zero_target_only_production_patches": target_only_patch_count == 0,
    }
    gate_passed = all(criteria.values())
    seed = {
        "manifest_sha256": first_report.get("manifest_sha256"),
        "first_run_id": first_report.get("run_id"),
        "second_run_id": second_report.get("run_id"),
        "criteria": criteria,
        "outcomes": outcomes,
    }
    return {
        "schema_version": 1,
        "manifest_name": manifest.name,
        "manifest_sha256": first_report.get("manifest_sha256"),
        "run_asof": first_report.get("run_asof"),
        "evaluation_id": _sha256_value(seed)[:20],
        "upstream": {
            "repository": upstream_repository,
            "revision": upstream_revision,
        },
        "first_run_id": first_report.get("run_id"),
        "second_run_id": second_report.get("run_id"),
        "summary": {
            "target_count": len(outcomes),
            "known_archetype_count": len(known),
            "discovery_count": len(discovery),
            "known_classified_count": known_classified_count,
            "known_generated_count": known_generated_count,
            "known_classification_rate": known_classification_rate,
            "known_generation_rate": known_generation_rate,
            "deterministic_count": deterministic_count,
            "reports_identical": reports_identical,
            "exception_failure_count": len(exception_failures),
            "exception_failures": exception_failures,
            "median_human_minutes": median_human_minutes,
            "target_only_patch_count": target_only_patch_count,
            "gate_passed": gate_passed,
        },
        "criteria": criteria,
        "fixture_evaluation": fixture_evaluation,
        "targets": outcomes,
    }


def run_batch_acceptance(
    *,
    manifest_path: str | Path,
    first_report_path: str | Path,
    second_report_path: str | Path,
    result_path: str | Path,
    upstream_repository: str,
    upstream_revision: str,
    target_only_patch_count: int = 0,
) -> dict[str, Any]:
    report = evaluate_batch_acceptance(
        load_manifest(manifest_path),
        load_result_report(first_report_path),
        load_result_report(second_report_path),
        upstream_repository=upstream_repository,
        upstream_revision=upstream_revision,
        target_only_patch_count=target_only_patch_count,
    )
    output = Path(result_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
