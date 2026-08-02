from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping

from civic_cartography.target_manifest import (
    ManifestError,
    Target,
    TargetManifest,
    load_manifest,
    manifest_to_dict,
)

UPSTREAM_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PASSING_MATCH_STATUSES = frozenset({"matched", "resolved"})
DETERMINISTIC_FIELDS = (
    "resolved_ocdids",
    "match_status",
    "inferred_classification",
    "classification_status",
    "generation_status",
    "division_paths",
    "jurisdiction_paths",
    "exception_class",
    "review_reason",
    "output_hashes",
)


class FixtureHarnessError(ValueError):
    """Raised when fixture reports cannot be evaluated safely."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureHarnessError(f"{location} must be a mapping")
    return dict(value)


def _require_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FixtureHarnessError(f"{location} must be a non-empty string")
    return value.strip()


def _manifest_sha256(manifest: TargetManifest) -> str:
    return _sha256_value(manifest_to_dict(manifest))


def load_result_report(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    try:
        raw = json.loads(report_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FixtureHarnessError(f"Result report not found: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise FixtureHarnessError(
            f"Result report JSON is invalid: {report_path}"
        ) from exc

    report = _require_mapping(raw, "result_report")
    required = {
        "schema_version",
        "manifest_name",
        "manifest_sha256",
        "run_asof",
        "run_id",
        "summary",
        "results",
    }
    missing = sorted(required - set(report))
    if missing:
        raise FixtureHarnessError(f"result_report is missing keys: {missing}")
    if report["schema_version"] != 1:
        raise FixtureHarnessError("result_report.schema_version must be 1")
    _require_nonempty_string(report["manifest_name"], "result_report.manifest_name")
    _require_nonempty_string(report["manifest_sha256"], "result_report.manifest_sha256")
    _require_nonempty_string(report["run_asof"], "result_report.run_asof")
    _require_nonempty_string(report["run_id"], "result_report.run_id")
    if not isinstance(report["results"], list):
        raise FixtureHarnessError("result_report.results must be a list")
    return report


def _index_results(report: Mapping[str, Any], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_result in enumerate(report["results"]):
        result = _require_mapping(raw_result, f"{label}.results[{index}]")
        target_id = _require_nonempty_string(
            result.get("target_id"), f"{label}.results[{index}].target_id"
        )
        if target_id in indexed:
            raise FixtureHarnessError(
                f"{label} contains duplicate target result: {target_id}"
            )
        indexed[target_id] = result
    return indexed


def _validate_report_pair(
    manifest: TargetManifest,
    first_report: Mapping[str, Any],
    second_report: Mapping[str, Any],
) -> None:
    expected_manifest_sha = _manifest_sha256(manifest)
    reports = (("first_report", first_report), ("second_report", second_report))
    for label, report in reports:
        if report["manifest_name"] != manifest.name:
            raise FixtureHarnessError(
                f"{label}.manifest_name does not match {manifest.name}"
            )
        if report["manifest_sha256"] != expected_manifest_sha:
            raise FixtureHarnessError(
                f"{label}.manifest_sha256 does not match the supplied manifest"
            )
    if first_report["run_asof"] != second_report["run_asof"]:
        raise FixtureHarnessError(
            "fixture reports must use the same deterministic run_asof timestamp"
        )


def _expected_hash_keys(result: Mapping[str, Any]) -> set[str]:
    division_paths = result.get("division_paths") or []
    jurisdiction_paths = result.get("jurisdiction_paths") or []
    if not isinstance(division_paths, list) or not isinstance(jurisdiction_paths, list):
        return set()
    return {str(path) for path in [*division_paths, *jurisdiction_paths]}


def _single_run_failures(
    target: Target, result: Mapping[str, Any], label: str
) -> list[str]:
    failures: list[str] = []
    if result.get("expected_classification") != target.expected_classification:
        failures.append(
            f"{label}: expected_classification does not match the manifest"
        )
    if result.get("match_status") not in PASSING_MATCH_STATUSES:
        failures.append(
            f"{label}: match_status={result.get('match_status')!r} is not resolved"
        )
    if result.get("inferred_classification") != target.expected_classification:
        failures.append(
            f"{label}: inferred classification does not equal "
            f"{target.expected_classification}"
        )
    if result.get("classification_status") != "matched":
        failures.append(f"{label}: classification_status must be 'matched'")
    if result.get("generation_status") != "generated":
        failures.append(f"{label}: generation_status must be 'generated'")
    division_paths = result.get("division_paths")
    jurisdiction_paths = result.get("jurisdiction_paths")
    if not isinstance(division_paths, list) or not division_paths:
        failures.append(f"{label}: at least one Division path is required")
    if not isinstance(jurisdiction_paths, list) or not jurisdiction_paths:
        failures.append(f"{label}: at least one Jurisdiction path is required")
    output_hashes = result.get("output_hashes")
    if not isinstance(output_hashes, dict) or not output_hashes:
        failures.append(f"{label}: output_hashes must be non-empty")
    elif set(output_hashes) != _expected_hash_keys(result):
        failures.append(
            f"{label}: output_hashes must cover every generated artifact path"
        )
    if result.get("exception_class") is not None:
        failures.append(
            f"{label}: generated fixture still has exception_class="
            f"{result.get('exception_class')!r}"
        )
    if result.get("review_reason") not in (None, ""):
        failures.append(f"{label}: generated fixture still has a review_reason")
    human_minutes = result.get("human_minutes")
    if (
        isinstance(human_minutes, bool)
        or not isinstance(human_minutes, (int, float))
        or human_minutes < 0
    ):
        failures.append(
            f"{label}: human_minutes must be recorded as a non-negative number"
        )
    return failures


def _determinism_failures(
    first_result: Mapping[str, Any], second_result: Mapping[str, Any]
) -> list[str]:
    failures: list[str] = []
    for field in DETERMINISTIC_FIELDS:
        if first_result.get(field) != second_result.get(field):
            failures.append(f"second_run: {field} differs from first_run")
    return failures


def _fixture_outcome(
    target: Target,
    first_result: Mapping[str, Any] | None,
    second_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    failures: list[str] = []
    if first_result is None:
        failures.append("first_run: fixture result is missing")
    if second_result is None:
        failures.append("second_run: fixture result is missing")

    if first_result is not None:
        failures.extend(_single_run_failures(target, first_result, "first_run"))
    if second_result is not None:
        failures.extend(_single_run_failures(target, second_result, "second_run"))
    if first_result is not None and second_result is not None:
        failures.extend(_determinism_failures(first_result, second_result))

    reference = first_result or second_result or {}
    deterministic = (
        first_result is not None
        and second_result is not None
        and not _determinism_failures(first_result, second_result)
    )
    return {
        "target_id": target.target_id,
        "jurisdiction_name": target.jurisdiction_name,
        "expected_archetype": target.expected_archetype,
        "expected_classification": target.expected_classification,
        "status": "passed" if not failures else "failed",
        "deterministic": deterministic,
        "resolved_ocdids": reference.get("resolved_ocdids", []),
        "inferred_classification": reference.get("inferred_classification"),
        "generation_status": reference.get("generation_status"),
        "division_paths": reference.get("division_paths", []),
        "jurisdiction_paths": reference.get("jurisdiction_paths", []),
        "output_hashes": reference.get("output_hashes", {}),
        "exception_class": reference.get("exception_class"),
        "review_reason": reference.get("review_reason"),
        "human_minutes": reference.get("human_minutes"),
        "failures": failures,
    }


def evaluate_fixture_reports(
    manifest: TargetManifest,
    first_report: Mapping[str, Any],
    second_report: Mapping[str, Any],
    *,
    upstream_repository: str,
    upstream_revision: str,
) -> dict[str, Any]:
    repository = _require_nonempty_string(
        upstream_repository, "upstream_repository"
    )
    revision = _require_nonempty_string(upstream_revision, "upstream_revision").lower()
    if not UPSTREAM_REVISION_PATTERN.fullmatch(revision):
        raise FixtureHarnessError(
            "upstream_revision must be a pinned 40-character lowercase commit SHA"
        )

    _validate_report_pair(manifest, first_report, second_report)
    first_by_id = _index_results(first_report, "first_report")
    second_by_id = _index_results(second_report, "second_report")
    fixture_targets = [
        target for target in manifest.targets if target.category == "regression_fixture"
    ]
    if not fixture_targets:
        raise FixtureHarnessError("manifest contains no regression fixtures")

    outcomes = [
        _fixture_outcome(
            target,
            first_by_id.get(target.target_id),
            second_by_id.get(target.target_id),
        )
        for target in fixture_targets
    ]
    passed_count = sum(outcome["status"] == "passed" for outcome in outcomes)
    deterministic_count = sum(outcome["deterministic"] for outcome in outcomes)
    report_content_match = _sha256_value(first_report) == _sha256_value(second_report)
    human_minutes = [
        float(outcome["human_minutes"])
        for outcome in outcomes
        if isinstance(outcome["human_minutes"], (int, float))
        and not isinstance(outcome["human_minutes"], bool)
    ]
    if len(human_minutes) == len(outcomes):
        median_human_minutes: float | None = statistics.median(human_minutes)
        human_review_gate = "passed" if median_human_minutes <= 10 else "failed"
    else:
        median_human_minutes = None
        human_review_gate = "not_evaluated"

    gate_passed = (
        passed_count == len(outcomes)
        and deterministic_count == len(outcomes)
        and report_content_match
        and human_review_gate == "passed"
    )
    summary = {
        "fixture_count": len(outcomes),
        "passed_count": passed_count,
        "failed_count": len(outcomes) - passed_count,
        "deterministic_count": deterministic_count,
        "report_content_match": report_content_match,
        "median_human_minutes": median_human_minutes,
        "human_review_gate": human_review_gate,
        "gate_passed": gate_passed,
    }
    seed = {
        "manifest_sha256": first_report["manifest_sha256"],
        "first_run_id": first_report["run_id"],
        "second_run_id": second_report["run_id"],
        "upstream_repository": repository,
        "upstream_revision": revision,
        "fixtures": outcomes,
    }
    return {
        "schema_version": 1,
        "manifest_name": manifest.name,
        "manifest_sha256": first_report["manifest_sha256"],
        "run_asof": first_report["run_asof"],
        "evaluation_id": _sha256_value(seed)[:20],
        "upstream": {
            "repository": repository,
            "revision": revision,
        },
        "first_run_id": first_report["run_id"],
        "second_run_id": second_report["run_id"],
        "summary": summary,
        "fixtures": outcomes,
    }


def write_fixture_report(report: Mapping[str, Any], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_fixture_harness(
    *,
    manifest_path: str | Path,
    first_report_path: str | Path,
    second_report_path: str | Path,
    result_path: str | Path,
    upstream_repository: str,
    upstream_revision: str,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    first_report = load_result_report(first_report_path)
    second_report = load_result_report(second_report_path)
    report = evaluate_fixture_reports(
        manifest,
        first_report,
        second_report,
        upstream_repository=upstream_repository,
        upstream_revision=upstream_revision,
    )
    write_fixture_report(report, result_path)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate all regression fixtures against two pinned upstream "
            "target-manifest result reports."
        )
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--first-report", required=True)
    parser.add_argument("--second-report", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument(
        "--upstream-repository",
        default="openstates/jurisdictions",
    )
    parser.add_argument("--upstream-revision", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_fixture_harness(
            manifest_path=args.target_manifest,
            first_report_path=args.first_report,
            second_report_path=args.second_report,
            result_path=args.result_path,
            upstream_repository=args.upstream_repository,
            upstream_revision=args.upstream_revision,
        )
    except (FixtureHarnessError, ManifestError) as exc:
        print(f"fixture-harness error: {exc}", file=sys.stderr)
        return 2

    summary = report["summary"]
    print(
        f"Evaluated {summary['fixture_count']} fixtures: "
        f"{summary['passed_count']} passed, {summary['failed_count']} failed "
        f"(evaluation_id={report['evaluation_id']})"
    )
    return 0 if summary["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
