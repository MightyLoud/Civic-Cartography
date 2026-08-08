from __future__ import annotations

import copy
import csv
import json

import pytest
import yaml

from civic_cartography.fixture_harness import _manifest_sha256
from civic_cartography.target_manifest import load_manifest
from scripts.finalize_measured_target import (
    MeasuredTargetFinalizerError,
    finalize_measured_target,
)


OCDID = "ocd-division/country:us/state:il/sewer:mwrd"
DIVISION_PATH = "divisions/il/local/mwrd.yaml"
JURISDICTION_PATH = "jurisdictions/il/local/mwrd.yaml"


def _write_inputs(tmp_path):
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "name": "mb100_041_test",
                "run_asof": "2026-08-08T04:00:00Z",
                "targets": [
                    {
                        "target_id": "MB100-041",
                        "jurisdiction_name": "Metropolitan Water Reclamation District",
                        "state": "il",
                        "selector": {"type": "ocdid", "value": OCDID},
                        "expected_archetype": "AR-D01",
                        "expected_classification": "special_purpose_district",
                        "category": "new_known_archetype",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    manifest = load_manifest(manifest_path)
    row = {
        "target_id": "MB100-041",
        "jurisdiction_name": "Metropolitan Water Reclamation District",
        "state": "il",
        "category": "new_known_archetype",
        "expected_archetype": "AR-D01",
        "requested_selector": {"type": "ocdid", "value": OCDID},
        "resolved_ocdids": [OCDID],
        "match_status": "matched",
        "expected_classification": "special_purpose_district",
        "inferred_classification": "special_purpose_district",
        "classification_status": "matched",
        "generation_status": "generated",
        "division_paths": [DIVISION_PATH],
        "jurisdiction_paths": [JURISDICTION_PATH],
        "exception_class": None,
        "review_reason": None,
        "human_minutes": 0.0,
        "output_hashes": {
            DIVISION_PATH: "a" * 64,
            JURISDICTION_PATH: "b" * 64,
        },
    }
    report = {
        "schema_version": 1,
        "manifest_name": manifest.name,
        "manifest_sha256": _manifest_sha256(manifest),
        "run_asof": "2026-08-08T04:00:00Z",
        "run_id": "run-1",
        "summary": {},
        "results": [row],
    }
    first_path = tmp_path / "run-1.json"
    second_path = tmp_path / "run-2.json"
    first_path.write_text(json.dumps(report), encoding="utf-8")
    second = copy.deepcopy(report)
    second["run_id"] = "run-2"
    second_path.write_text(json.dumps(second), encoding="utf-8")

    source_path = tmp_path / "source-manifest.json"
    source_path.write_text(
        json.dumps(
            {
                "version": 1,
                "files": {
                    "master": {
                        "path": "country-us.csv",
                        "url": "https://example.test/country-us.csv",
                        "sha256": "c" * 64,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest_path, first_path, second_path, source_path


def test_finalizer_registers_only_complete_target(tmp_path) -> None:
    manifest, first, second, source = _write_inputs(tmp_path)
    completion = tmp_path / "completion-manifest.json"
    register = tmp_path / "completion-register.csv"

    result = finalize_measured_target(
        manifest_path=manifest,
        first_report_path=first,
        second_report_path=second,
        source_manifest_path=source,
        completion_manifest_path=completion,
        register_path=register,
        evidence_ref="evidence/measured-batch-100/mb100-041/completion-manifest.json",
    )

    assert result["target_id"] == "MB100-041"
    assert result["complete_ok"] is True
    emitted = json.loads(completion.read_text(encoding="utf-8"))
    assert emitted["targets"][0]["complete_ok"] is True
    with register.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["target_id"] == "MB100-041"
    assert rows[0]["complete_ok"] == "TRUE"
    assert rows[0]["qa_ok"] == "TRUE"
    assert rows[0]["evidence_ref"].endswith("completion-manifest.json")


def test_failed_completion_is_retained_but_never_registered(tmp_path) -> None:
    manifest, first, second, source = _write_inputs(tmp_path)
    second_report = json.loads(second.read_text(encoding="utf-8"))
    second_report["results"][0]["output_hashes"][JURISDICTION_PATH] = "d" * 64
    second.write_text(json.dumps(second_report), encoding="utf-8")
    completion = tmp_path / "completion-manifest.json"
    register = tmp_path / "completion-register.csv"

    with pytest.raises(MeasuredTargetFinalizerError, match="failed_gates"):
        finalize_measured_target(
            manifest_path=manifest,
            first_report_path=first,
            second_report_path=second,
            source_manifest_path=source,
            completion_manifest_path=completion,
            register_path=register,
            evidence_ref="evidence/measured-batch-100/mb100-041/completion-manifest.json",
        )

    emitted = json.loads(completion.read_text(encoding="utf-8"))
    assert emitted["targets"][0]["complete_ok"] is False
    assert emitted["targets"][0]["failed_gates"] == ["parity_ok"]
    assert not register.exists()
