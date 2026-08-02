from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from civic_cartography.fixture_harness import (
    FixtureHarnessError,
    evaluate_fixture_reports,
    main,
)
from civic_cartography.target_manifest import build_report, load_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "batch_pilot_25.yml"
FIXTURE_REPORT_SCHEMA = (
    PROJECT_ROOT / "schemas" / "regression-fixture-report.schema.json"
)
RUN_ASOF = "2026-08-02T09:00:00-06:00"
UPSTREAM_REVISION = "6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705"
FIXTURE_IDS = {
    "BP25-001",
    "BP25-002",
    "BP25-009",
    "BP25-014",
    "BP25-018",
    "BP25-022",
}
EXPLICIT_RESOLUTIONS = {
    "BP25-014": [
        "ocd-division/country:us/state:co/school_district:colorado_springs_11"
    ],
    "BP25-018": [
        "ocd-division/country:us/state:co/special_district:regional_transportation"
    ],
    "BP25-022": ["ocd-division/country:us/state:co/place:denver"],
}


def _fixture_overlays(manifest, artifact_root: Path) -> dict[str, dict[str, object]]:
    overlays: dict[str, dict[str, object]] = {}
    for target in manifest.targets:
        if target.target_id not in FIXTURE_IDS:
            continue
        slug = target.target_id.lower()
        division_path = Path("divisions") / target.state / "local" / f"{slug}.yaml"
        jurisdiction_path = (
            Path("jurisdictions") / target.state / "local" / f"{slug}.yaml"
        )
        (artifact_root / division_path).parent.mkdir(parents=True, exist_ok=True)
        (artifact_root / jurisdiction_path).parent.mkdir(parents=True, exist_ok=True)
        (artifact_root / division_path).write_text(
            f"target_id: {target.target_id}\nkind: division\n",
            encoding="utf-8",
        )
        (artifact_root / jurisdiction_path).write_text(
            f"target_id: {target.target_id}\n"
            f"classification: {target.expected_classification}\n",
            encoding="utf-8",
        )
        if target.selector["type"] == "ocdid":
            resolved_ocdids = [target.selector["value"]]
        else:
            resolved_ocdids = EXPLICIT_RESOLUTIONS[target.target_id]
        overlays[target.target_id] = {
            "resolved_ocdids": resolved_ocdids,
            "match_status": "matched",
            "inferred_classification": target.expected_classification,
            "classification_status": "matched",
            "generation_status": "generated",
            "division_paths": [division_path.as_posix()],
            "jurisdiction_paths": [jurisdiction_path.as_posix()],
            "exception_class": None,
            "review_reason": None,
            "human_minutes": 5.0,
        }
    return overlays


def _report_pair(tmp_path: Path):
    manifest = load_manifest(PILOT_MANIFEST)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_overlays = _fixture_overlays(manifest, first_root)
    second_overlays = _fixture_overlays(manifest, second_root)
    first = build_report(
        manifest,
        run_asof=RUN_ASOF,
        execution_results=first_overlays,
        execution_results_sha256="fixture-capture-v1",
        artifact_root=first_root,
    )
    second = build_report(
        manifest,
        run_asof=RUN_ASOF,
        execution_results=second_overlays,
        execution_results_sha256="fixture-capture-v1",
        artifact_root=second_root,
    )
    return manifest, first, second


def test_all_six_fixtures_pass_with_identical_upstream_reports(
    tmp_path: Path,
) -> None:
    manifest, first, second = _report_pair(tmp_path)

    evaluation = evaluate_fixture_reports(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"] == {
        "fixture_count": 6,
        "passed_count": 6,
        "failed_count": 0,
        "deterministic_count": 6,
        "report_content_match": True,
        "median_human_minutes": 5.0,
        "human_review_gate": "passed",
        "gate_passed": True,
    }
    schema = json.loads(FIXTURE_REPORT_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(evaluation)


def test_fixture_harness_enforces_review_time_gate(tmp_path: Path) -> None:
    manifest, first, second = _report_pair(tmp_path)
    for report in (first, second):
        for result in report["results"]:
            if result["target_id"] in FIXTURE_IDS:
                result["human_minutes"] = 15.0
    first["run_id"] = second["run_id"] = "same-slow-review-capture"

    evaluation = evaluate_fixture_reports(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["passed_count"] == 6
    assert evaluation["summary"]["human_review_gate"] == "failed"
    assert evaluation["summary"]["gate_passed"] is False


def test_fixture_harness_detects_artifact_hash_drift(tmp_path: Path) -> None:
    manifest, first, second = _report_pair(tmp_path)
    second = deepcopy(second)
    target = next(row for row in second["results"] if row["target_id"] == "BP25-001")
    path = next(iter(target["output_hashes"]))
    target["output_hashes"][path] = "f" * 64

    evaluation = evaluate_fixture_reports(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )
    seattle = next(
        row for row in evaluation["fixtures"] if row["target_id"] == "BP25-001"
    )

    assert seattle["deterministic"] is False
    assert "second_run: output_hashes differs from first_run" in seattle["failures"]
    assert evaluation["summary"]["report_content_match"] is False
    assert evaluation["summary"]["gate_passed"] is False


def test_fixture_harness_preserves_explicit_generation_exception(
    tmp_path: Path,
) -> None:
    manifest, first, second = _report_pair(tmp_path)
    for report in (first, second):
        rtd = next(row for row in report["results"] if row["target_id"] == "BP25-018")
        rtd.update(
            {
                "generation_status": "failed",
                "division_paths": [],
                "jurisdiction_paths": [],
                "output_hashes": {},
                "exception_class": "unsupported_special_district_generation",
                "review_reason": "Upstream generator does not yet emit RTD YAML.",
            }
        )
    first["run_id"] = second["run_id"] = "same-explicit-exception"

    evaluation = evaluate_fixture_reports(
        manifest,
        first,
        second,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )
    rtd = next(row for row in evaluation["fixtures"] if row["target_id"] == "BP25-018")

    assert rtd["status"] == "failed"
    assert rtd["exception_class"] == "unsupported_special_district_generation"
    assert rtd["review_reason"] == "Upstream generator does not yet emit RTD YAML."


def test_fixture_harness_rejects_unpinned_upstream_revision(tmp_path: Path) -> None:
    manifest, first, second = _report_pair(tmp_path)

    with pytest.raises(FixtureHarnessError, match="40-character"):
        evaluate_fixture_reports(
            manifest,
            first,
            second,
            upstream_repository="openstates/jurisdictions",
            upstream_revision="main",
        )


def test_fixture_harness_cli_writes_failed_gate_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, first, second = _report_pair(tmp_path)
    second = deepcopy(second)
    second["results"] = [
        row for row in second["results"] if row["target_id"] != "BP25-009"
    ]
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    output_path = tmp_path / "fixture-evaluation.json"
    first_path.write_text(json.dumps(first), encoding="utf-8")
    second_path.write_text(json.dumps(second), encoding="utf-8")

    exit_code = main(
        [
            "--target-manifest",
            str(PILOT_MANIFEST),
            "--first-report",
            str(first_path),
            "--second-report",
            str(second_path),
            "--result-path",
            str(output_path),
            "--upstream-revision",
            UPSTREAM_REVISION,
        ]
    )

    assert exit_code == 1
    evaluation = json.loads(output_path.read_text(encoding="utf-8"))
    assert evaluation["summary"]["failed_count"] >= 1
    assert "6 fixtures" in capsys.readouterr().out
