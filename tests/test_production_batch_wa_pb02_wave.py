from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from civic_cartography.production_wave import (
    ProductionWaveError,
    build_artifact_inventory,
    evaluate_production_wave,
    load_crosswalk,
    select_production_wave,
)
from civic_cartography.target_manifest import build_report, load_manifest


ROOT = Path(__file__).resolve().parents[1]
FULL_MANIFEST_PATH = ROOT / "tests" / "fixtures" / "production_batch_wa_65.yml"
CROSSWALK_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-65"
    / "selection"
    / "selection-crosswalk.json"
)
UPSTREAM_REVISION = "6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705"
RUN_ASOF = "2026-08-04T18:00:00Z"
WAVE_SCHEMA_PATH = ROOT / "schemas" / "production-wave-report.schema.json"


def _reports(tmp_path: Path) -> tuple[object, dict, dict, dict, dict]:
    manifest = select_production_wave(
        load_manifest(FULL_MANIFEST_PATH), "WA-PB02-A"
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
    inventory = build_artifact_inventory(tmp_path, first)
    return (
        manifest,
        first,
        copy.deepcopy(first),
        inventory,
        copy.deepcopy(inventory),
    )


def test_wave_a_selection_is_the_frozen_first_twenty_targets() -> None:
    wave = select_production_wave(
        load_manifest(FULL_MANIFEST_PATH), "WA-PB02-A"
    )

    assert [target.target_id for target in wave.targets] == [
        f"WA-PB02-{number:03d}" for number in range(1, 21)
    ]
    assert wave.targets[0].jurisdiction_name == "Roslyn"
    assert wave.targets[-1].jurisdiction_name == "Spangle"
    assert {target.wave for target in wave.targets} == {"WA-PB02-A"}


def test_wave_a_acceptance_uses_the_reusable_wave_contract(tmp_path: Path) -> None:
    manifest, first, second, first_inventory, second_inventory = _reports(tmp_path)
    evaluation = evaluate_production_wave(
        manifest,
        first,
        second,
        load_crosswalk(CROSSWALK_PATH),
        first_inventory,
        second_inventory,
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
        "artifact_count": 40,
        "target_artifact_count": 40,
        "shared_artifact_count": 0,
        "artifact_inventories_identical": True,
        "target_only_patch_count": 0,
        "gate_passed": True,
    }
    assert evaluation["batch_id"] == "WA-PB02"
    assert evaluation["wave"] == "WA-PB02-A"
    assert all(evaluation["criteria"].values())
    schema = json.loads(WAVE_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(evaluation)


def test_wave_a_rejects_crosswalk_from_a_different_batch(tmp_path: Path) -> None:
    manifest, first, second, first_inventory, second_inventory = _reports(tmp_path)
    crosswalk = load_crosswalk(CROSSWALK_PATH)
    crosswalk["batch_id"] = "WA-PB01"

    with pytest.raises(
        ProductionWaveError, match="crosswalk batch_id does not match"
    ):
        evaluate_production_wave(
            manifest,
            first,
            second,
            crosswalk,
            first_inventory,
            second_inventory,
            upstream_repository="openstates/jurisdictions",
            upstream_revision=UPSTREAM_REVISION,
        )


def test_wave_a_rejects_flattened_nesting(tmp_path: Path) -> None:
    manifest, first, second, first_inventory, second_inventory = _reports(tmp_path)
    crosswalk = load_crosswalk(CROSSWALK_PATH)
    crosswalk["candidates"][0]["nesting"]["county_fips"] = "037"

    evaluation = evaluate_production_wave(
        manifest,
        first,
        second,
        crosswalk,
        first_inventory,
        second_inventory,
        upstream_repository="openstates/jurisdictions",
        upstream_revision=UPSTREAM_REVISION,
    )

    assert evaluation["summary"]["nesting_parity_count"] == 19
    assert evaluation["criteria"][
        "all_nesting_relationships_preserved_as_lists"
    ] is False


def test_pb02_wave_a_workflow_invokes_only_its_matching_runner() -> None:
    workflow = (
        ROOT
        / ".github"
        / "workflows"
        / "validate-production-batch-wa-pb02-wave-a.yml"
    ).read_text(encoding="utf-8")
    runner_lines = [
        line.strip()
        for line in workflow.splitlines()
        if "run: bash scripts/run_production_batch_wa_pb02_wave_" in line
    ]

    assert runner_lines == [
        "run: bash scripts/run_production_batch_wa_pb02_wave_a_ci.sh"
    ]
