from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from civic_cartography.target_manifest import (
    ManifestError,
    build_report,
    load_execution_results,
    load_manifest,
    main,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "batch_pilot_25.yml"
MANIFEST_SCHEMA = PROJECT_ROOT / "schemas" / "target-manifest.schema.json"
REPORT_SCHEMA = PROJECT_ROOT / "schemas" / "target-result-report.schema.json"
RUN_ASOF = "2026-08-02T09:00:00-06:00"


def test_batch_pilot_manifest_matches_control_totals() -> None:
    manifest = load_manifest(PILOT_MANIFEST)

    assert len(manifest.targets) == 25
    assert len({target.state for target in manifest.targets}) == 14
    assert (
        sum(target.category == "regression_fixture" for target in manifest.targets)
        == 6
    )
    assert sum(target.category == "discovery" for target in manifest.targets) == 4
    assert [target.target_id for target in manifest.targets] == [
        f"BP25-{index:03d}" for index in range(1, 26)
    ]


def test_batch_pilot_manifest_satisfies_json_schema() -> None:
    instance = yaml.safe_load(PILOT_MANIFEST.read_text(encoding="utf-8"))
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(instance)


def test_report_is_deterministic_and_emits_one_result_per_target() -> None:
    manifest = load_manifest(PILOT_MANIFEST)

    first = build_report(manifest, run_asof=RUN_ASOF)
    second = build_report(manifest, run_asof=RUN_ASOF)

    assert first == second
    assert first["run_asof"] == "2026-08-02T15:00:00Z"
    assert first["summary"]["target_count"] == 25
    assert first["summary"]["state_count"] == 14
    assert first["summary"]["fixture_count"] == 6
    assert first["summary"]["discovery_count"] == 4
    assert len(first["results"]) == 25
    assert {row["target_id"] for row in first["results"]} == {
        f"BP25-{index:03d}" for index in range(1, 26)
    }

    by_id = {row["target_id"]: row for row in first["results"]}
    assert by_id["BP25-001"]["match_status"] == "resolved"
    assert by_id["BP25-001"]["resolved_ocdids"] == [
        "ocd-division/country:us/state:wa/place:seattle"
    ]
    assert by_id["BP25-014"]["exception_class"] == "explicit_lookup_required"
    assert by_id["BP25-022"]["exception_class"] == "alias_resolution_required"
    assert by_id["BP25-022"]["resolved_ocdids"] == [
        "ocd-division/country:us/state:co/place:denver",
        "ocd-division/country:us/state:co/county:denver",
    ]

    report_schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(report_schema).validate(first)


def test_report_requires_explicit_timezone_aware_run_timestamp() -> None:
    manifest = load_manifest(PILOT_MANIFEST)

    with pytest.raises(ManifestError, match="run_asof"):
        build_report(manifest)

    with pytest.raises(ManifestError, match="timezone"):
        build_report(manifest, run_asof="2026-08-02T09:00:00")


def test_execution_overlay_records_generation_and_hashes_artifacts(
    tmp_path: Path,
) -> None:
    manifest = load_manifest(PILOT_MANIFEST)
    division_path = Path("divisions/wa/local/seattle.yaml")
    jurisdiction_path = Path("jurisdictions/wa/local/seattle.yaml")
    (tmp_path / division_path).parent.mkdir(parents=True)
    (tmp_path / jurisdiction_path).parent.mkdir(parents=True)
    (tmp_path / division_path).write_text("ocdid: seattle\n", encoding="utf-8")
    (tmp_path / jurisdiction_path).write_text(
        "classification: government\n", encoding="utf-8"
    )

    overlay = {
        "BP25-001": {
            "match_status": "matched",
            "inferred_classification": "government",
            "classification_status": "matched",
            "generation_status": "generated",
            "division_paths": [division_path.as_posix()],
            "jurisdiction_paths": [jurisdiction_path.as_posix()],
            "exception_class": None,
            "review_reason": None,
            "human_minutes": 2.5,
        }
    }
    report = build_report(
        manifest,
        run_asof=RUN_ASOF,
        execution_results=overlay,
        execution_results_sha256="adapter-result-sha",
        artifact_root=tmp_path,
    )
    result = report["results"][0]

    assert result["generation_status"] == "generated"
    assert result["classification_status"] == "matched"
    assert result["human_minutes"] == 2.5
    assert result["output_hashes"] == {
        division_path.as_posix(): hashlib.sha256(
            (tmp_path / division_path).read_bytes()
        ).hexdigest(),
        jurisdiction_path.as_posix(): hashlib.sha256(
            (tmp_path / jurisdiction_path).read_bytes()
        ).hexdigest(),
    }


def test_execution_results_reject_unknown_target(tmp_path: Path) -> None:
    path = tmp_path / "execution.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "results": {
                    "BP25-999": {
                        "generation_status": "failed",
                        "exception_class": "unknown",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="unknown targets"):
        load_execution_results(path, {"BP25-001"})


def test_generated_result_requires_existing_contained_artifact_path(
    tmp_path: Path,
) -> None:
    manifest = load_manifest(PILOT_MANIFEST)
    overlay = {
        "BP25-001": {
            "match_status": "matched",
            "inferred_classification": "government",
            "classification_status": "matched",
            "generation_status": "generated",
            "division_paths": ["../escape.yaml"],
            "exception_class": None,
            "review_reason": None,
        }
    }

    with pytest.raises(ManifestError, match="contained"):
        build_report(
            manifest,
            run_asof=RUN_ASOF,
            execution_results=overlay,
            artifact_root=tmp_path,
        )


def test_duplicate_target_ids_are_rejected(tmp_path: Path) -> None:
    raw = yaml.safe_load(PILOT_MANIFEST.read_text(encoding="utf-8"))
    raw["targets"][1]["target_id"] = raw["targets"][0]["target_id"]
    path = tmp_path / "duplicate.yml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ManifestError, match="must be unique"):
        load_manifest(path)


def test_territory_ocdid_is_valid_for_matching_postal_code(tmp_path: Path) -> None:
    raw = {
        "version": 1,
        "name": "territory-target",
        "targets": [
            {
                "target_id": "MB100-050",
                "jurisdiction_name": "San Juan Municipio",
                "state": "pr",
                "selector": {
                    "type": "ocdid",
                    "value": (
                        "ocd-division/country:us/territory:pr/"
                        "municipio:san_juan"
                    ),
                },
                "expected_archetype": "DISCOVERY — TERRITORY MUNICIPIO",
                "expected_classification": "government",
                "category": "discovery",
            }
        ],
    }
    path = tmp_path / "territory.yml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    manifest = load_manifest(path)
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(raw)

    assert manifest.targets[0].state == "pr"
    assert manifest.targets[0].selector["value"].endswith(
        "/territory:pr/municipio:san_juan"
    )


def test_territory_ocdid_must_match_target_postal_code(tmp_path: Path) -> None:
    raw = {
        "version": 1,
        "name": "mismatched-territory-target",
        "targets": [
            {
                "target_id": "MISMATCH",
                "jurisdiction_name": "San Juan Municipio",
                "state": "gu",
                "selector": {
                    "type": "ocdid",
                    "value": (
                        "ocd-division/country:us/territory:pr/"
                        "municipio:san_juan"
                    ),
                },
                "expected_archetype": "DISCOVERY",
                "expected_classification": "government",
                "category": "discovery",
            }
        ],
    }
    path = tmp_path / "mismatch.yml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ManifestError, match="territory:gu"):
        load_manifest(path)


def test_cli_writes_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "report.json"

    exit_code = main(
        [
            "--target-manifest",
            str(PILOT_MANIFEST),
            "--run-asof",
            RUN_ASOF,
            "--result-path",
            str(output),
        ]
    )

    assert exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["summary"]["target_count"] == 25
    assert "Wrote 25 target results" in capsys.readouterr().out
