from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from civic_cartography.production_wave import (
    ProductionWaveError,
    evaluate_production_wave,
    load_crosswalk,
    select_production_wave,
)
from civic_cartography.target_manifest import build_report, load_manifest


ROOT = Path(__file__).resolve().parents[1]
FULL_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "production_batch_wa_100.yml"
CROSSWALK_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-100"
    / "selection"
    / "selection-crosswalk.json"
)
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "target-manifest.schema.json"
RESULT_SCHEMA_PATH = ROOT / "schemas" / "target-result-report.schema.json"
WAVE_SCHEMA_PATH = ROOT / "schemas" / "production-wave-report.schema.json"
UPSTREAM_REVISION = "6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705"
RUN_ASOF = "2026-08-03T18:00:00Z"


def _reports(tmp_path: Path) -> tuple[object, dict, dict]:
    manifest = select_production_wave(
        load_manifest(FULL_MANIFEST_PATH), "WA-PB01-A"
    )
    overlays: dict[str, dict[str, object]] = {}
    for target in manifest.targets:
        slug = target.target_id.lower()
        division_path = Path("divisions/wa/local") / f"{slug}.yaml"
        jurisdiction_path = Path("jurisdictions/wa/local") / f"{slug}.yaml"
        for path, content in (
            (division_path, f"id: {target.selector['value']}\n"),
            (jurisdiction_path, "classification: government\n"),
        ):
            (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / path).write_text(content, encoding="utf-8")
        overlays[target.target_id] = {
            "resolved_ocdids": [target.selector["value"]],
            "match_status": "matched",
            "inferred_classification": "government",
            "classification_status": "matched",
            "generation_status": "generated",
            "division_paths": [division_path.as_posix()],
            "jurisdiction_paths": [jurisdiction_path.as_posix()],
            "exception_class": None,
            "review_reason": None,
            "human_minutes": 0.0,
        }
    first = build_report(
        manifest,
        run_asof=RUN_ASOF,
        execution_results=overlays,
        execution_results_sha256="synthetic-overlay",
        artifact_root=tmp_path,
    )
    return manifest, first, copy.deepcopy(first)


def test_full_production_manifest_is_executable_and_satisfies_schema() -> None:
    manifest = load_manifest(FULL_MANIFEST_PATH)
    assert len(manifest.targets) == 100
    assert manifest.state == "wa"
    assert manifest.source_manifest is not None
    assert manifest.selection_crosswalk is not None
    assert {target.category for target in manifest.targets} == {"production"}
    assert {target.wave for target in manifest.targets} == {
        f"WA-PB01-{letter}" for letter in "ABCDE"
    }

    instance = yaml.safe_load(FULL_MANIFEST_PATH.read_text(encoding="utf-8"))
    schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(instance)


def test_wave_a_selection_is_the_frozen_first_twenty_targets() -> None:
    wave = select_production_wave(
        load_manifest(FULL_MANIFEST_PATH), "WA-PB01-A"
    )
    assert [target.target_id for target in wave.targets] == [
        f"WA-PB01-{number:03d}" for number in range(1, 21)
    ]
    assert wave.targets[0].jurisdiction_name == "Ione"
    assert wave.targets[-1].jurisdiction_name == "Langley"
    assert {target.wave for target in wave.targets} == {"WA-PB01-A"}


def test_wave_a_acceptance_passes_all_gates_and_schemas(tmp_path: Path) -> None:
    manifest, first, second = _reports(tmp_path)
    evaluation = evaluate_production_wave(
        manifest,
        first,
        second,
        load_crosswalk(CROSSWALK_PATH),
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"] == {
        "target_count": 20,
        "passed_count": 20,
        "deterministic_count": 20,
        "nesting_parity_count": 20,
        "reports_identical": True,
        "unique_output_paths": True,
        "target_only_patch_count": 0,
        "gate_passed": True,
    }
    assert all(evaluation["criteria"].values())

    result_schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    wave_schema = json.loads(WAVE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(result_schema).validate(first)
    Draft202012Validator(wave_schema).validate(evaluation)


def test_wave_a_rejects_a_non_exact_ocdid(tmp_path: Path) -> None:
    manifest, first, second = _reports(tmp_path)
    for report in (first, second):
        report["results"][0]["resolved_ocdids"] = [
            "ocd-division/country:us/state:wa/place:not_ione"
        ]

    evaluation = evaluate_production_wave(
        manifest,
        first,
        second,
        load_crosswalk(CROSSWALK_PATH),
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["passed_count"] == 19
    assert evaluation["summary"]["gate_passed"] is False
    assert "resolved_ocdids must equal the exact selector" in " ".join(
        evaluation["targets"][0]["failures"]
    )


def test_wave_a_rejects_flattened_nesting(tmp_path: Path) -> None:
    manifest, first, second = _reports(tmp_path)
    crosswalk = load_crosswalk(CROSSWALK_PATH)
    first_row = next(
        row for row in crosswalk["candidates"] if row.get("target_id") == "WA-PB01-001"
    )
    first_row["nesting"]["county_fips"] = "051"

    evaluation = evaluate_production_wave(
        manifest,
        first,
        second,
        crosswalk,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["nesting_parity_count"] == 19
    assert evaluation["criteria"][
        "all_nesting_relationships_preserved_as_lists"
    ] is False


def test_wave_selection_rejects_an_incomplete_wave() -> None:
    manifest = load_manifest(FULL_MANIFEST_PATH)
    with pytest.raises(ProductionWaveError, match="exactly 21"):
        select_production_wave(
            manifest, "WA-PB01-A", expected_target_count=21
        )
