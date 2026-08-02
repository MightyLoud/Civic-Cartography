from __future__ import annotations

import copy
from pathlib import Path

from civic_cartography.batch_acceptance import evaluate_batch_acceptance
from civic_cartography.fixture_harness import _manifest_sha256
from civic_cartography.target_manifest import Target, load_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "tests" / "fixtures" / "batch_pilot_25.yml"
UPSTREAM_REVISION = "0" * 40


def _result(target: Target, *, accepted: bool) -> dict[str, object]:
    if accepted:
        division_path = f"divisions/{target.target_id.lower()}.yaml"
        jurisdiction_path = f"jurisdictions/{target.target_id.lower()}.yaml"
        return {
            "target_id": target.target_id,
            "jurisdiction_name": target.jurisdiction_name,
            "state": target.state,
            "category": target.category,
            "expected_archetype": target.expected_archetype,
            "requested_selector": target.selector,
            "resolved_ocdids": [f"ocd-division/country:us/state:{target.state}/test:x"],
            "match_status": "matched",
            "expected_classification": target.expected_classification,
            "inferred_classification": target.expected_classification,
            "classification_status": "matched",
            "generation_status": "generated",
            "division_paths": [division_path],
            "jurisdiction_paths": [jurisdiction_path],
            "exception_class": None,
            "review_reason": None,
            "human_minutes": 0.0,
            "output_hashes": {
                division_path: "a" * 64,
                jurisdiction_path: "b" * 64,
            },
        }
    return {
        "target_id": target.target_id,
        "jurisdiction_name": target.jurisdiction_name,
        "state": target.state,
        "category": target.category,
        "expected_archetype": target.expected_archetype,
        "requested_selector": target.selector,
        "resolved_ocdids": [],
        "match_status": "not_found",
        "expected_classification": target.expected_classification,
        "inferred_classification": None,
        "classification_status": "not_evaluated",
        "generation_status": "skipped",
        "division_paths": [],
        "jurisdiction_paths": [],
        "exception_class": "upstream_target_not_found",
        "review_reason": "No maintained or upstream candidate resolved this target.",
        "human_minutes": 0.0,
        "output_hashes": {},
    }


def _reports(*, additional_known_failures: int = 0) -> tuple[object, dict, dict]:
    manifest = load_manifest(MANIFEST_PATH)
    known_failures = {"BP25-015", "BP25-023", "BP25-024"}
    if additional_known_failures:
        known_failures.add("BP25-017")
    discovery_failures = {
        target.target_id for target in manifest.targets if target.category == "discovery"
    }
    failures = known_failures | discovery_failures
    results = [
        _result(target, accepted=target.target_id not in failures)
        for target in manifest.targets
    ]
    report = {
        "schema_version": 1,
        "manifest_name": manifest.name,
        "manifest_sha256": _manifest_sha256(manifest),
        "run_asof": "2026-08-02T15:00:00Z",
        "run_id": "synthetic-batch-run",
        "summary": {},
        "results": results,
    }
    return manifest, report, copy.deepcopy(report)


def test_batch_acceptance_passes_at_exact_eighty_percent() -> None:
    manifest, first, second = _reports()

    evaluation = evaluate_batch_acceptance(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["target_count"] == 25
    assert evaluation["summary"]["known_classified_count"] == 12
    assert evaluation["summary"]["known_generated_count"] == 12
    assert evaluation["summary"]["known_classification_rate"] == 0.8
    assert evaluation["summary"]["known_generation_rate"] == 0.8
    assert evaluation["summary"]["gate_passed"] is True


def test_batch_acceptance_rejects_below_eighty_percent() -> None:
    manifest, first, second = _reports(additional_known_failures=1)

    evaluation = evaluate_batch_acceptance(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["known_classified_count"] == 11
    assert evaluation["criteria"][
        "known_classification_rate_at_least_80_percent"
    ] is False
    assert evaluation["criteria"][
        "known_generation_rate_at_least_80_percent"
    ] is False
    assert evaluation["summary"]["gate_passed"] is False


def test_batch_acceptance_requires_explicit_exception_reason() -> None:
    manifest, first, second = _reports()
    for report in (first, second):
        target = next(
            row for row in report["results"] if row["target_id"] == "BP25-023"
        )
        target["review_reason"] = None

    evaluation = evaluate_batch_acceptance(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["exception_failures"] == ["BP25-023"]
    assert evaluation["criteria"]["all_failures_have_explicit_exception"] is False
    assert evaluation["summary"]["gate_passed"] is False
