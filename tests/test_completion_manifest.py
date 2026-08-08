from __future__ import annotations

import copy

import pytest

from civic_cartography.completion_manifest import (
    CompletionManifestError,
    evaluate_completion_manifest,
)
from civic_cartography.fixture_harness import _manifest_sha256
from civic_cartography.target_manifest import Target, TargetManifest


OCDID = "ocd-division/country:us/state:wa/place:testville"
DIVISION_PATH = "divisions/wa/local/testville.yaml"
JURISDICTION_PATH = "jurisdictions/wa/local/testville.yaml"


def _manifest() -> TargetManifest:
    return TargetManifest(
        version=1,
        name="completion_test",
        description=None,
        run_asof="2026-08-08T03:30:00Z",
        targets=(
            Target(
                target_id="TEST-001",
                jurisdiction_name="Testville",
                state="wa",
                selector={"type": "ocdid", "value": OCDID},
                expected_archetype="AR-001",
                expected_classification="government",
                category="new_known_archetype",
            ),
        ),
    )


def _report() -> dict:
    manifest = _manifest()
    row = {
        "target_id": "TEST-001",
        "jurisdiction_name": "Testville",
        "state": "wa",
        "category": "new_known_archetype",
        "expected_archetype": "AR-001",
        "requested_selector": {"type": "ocdid", "value": OCDID},
        "resolved_ocdids": [OCDID],
        "match_status": "matched",
        "expected_classification": "government",
        "inferred_classification": "government",
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
    return {
        "schema_version": 1,
        "manifest_name": manifest.name,
        "manifest_sha256": _manifest_sha256(manifest),
        "run_asof": "2026-08-08T03:30:00Z",
        "run_id": "run-1",
        "summary": {},
        "results": [row],
    }


def _source_manifest() -> dict:
    return {
        "version": 1,
        "files": {
            "master": {
                "path": "country-us.csv",
                "url": "https://example.test/country-us.csv",
                "sha256": "d" * 64,
                "size_bytes": 100,
            }
        },
    }


def _evaluate(first: dict, second: dict, source: dict | None = None) -> dict:
    return evaluate_completion_manifest(
        _manifest(), first, second, source or _source_manifest()
    )


def test_complete_target_passes_every_gate() -> None:
    first = _report()
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"

    evaluation = _evaluate(first, second)
    target = evaluation["targets"][0]

    assert evaluation["summary"]["complete_count"] == 1
    assert evaluation["summary"]["all_complete"] is True
    assert target["raw_exists"] is True
    assert target["normalized_exists"] is True
    assert target["identifier_join_ok"] is True
    assert target["qa_ok"] is True
    assert target["parity_ok"] is True
    assert target["source_provenance_ok"] is True
    assert target["complete_ok"] is True
    assert target["confidence"] == "HIGH"
    assert target["failed_gates"] == []


def test_checksum_drift_blocks_parity_and_completion() -> None:
    first = _report()
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"
    second["results"][0]["output_hashes"][JURISDICTION_PATH] = "e" * 64

    target = _evaluate(first, second)["targets"][0]

    assert target["normalized_exists"] is True
    assert target["qa_ok"] is True
    assert target["parity_ok"] is False
    assert target["complete_ok"] is False
    assert target["failed_gates"] == ["parity_ok"]


def test_missing_source_hash_blocks_raw_and_provenance() -> None:
    first = _report()
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"
    source = {
        "version": 1,
        "files": {
            "master": {
                "path": "country-us.csv",
                "url": "https://example.test/country-us.csv",
            }
        },
    }

    target = _evaluate(first, second, source)["targets"][0]

    assert target["raw_exists"] is False
    assert target["source_provenance_ok"] is False
    assert target["complete_ok"] is False
    assert target["failed_gates"] == ["raw_exists", "source_provenance_ok"]


def test_wrong_resolved_identifier_blocks_join_and_completion() -> None:
    first = _report()
    first["results"][0]["resolved_ocdids"] = [
        "ocd-division/country:us/state:wa/place:wrong"
    ]
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"

    target = _evaluate(first, second)["targets"][0]

    assert target["identifier_join_ok"] is False
    assert target["qa_ok"] is True
    assert target["complete_ok"] is False
    assert target["failed_gates"] == ["identifier_join_ok"]


def test_missing_normalized_artifact_blocks_qa_and_completion() -> None:
    first = _report()
    first["results"][0]["jurisdiction_paths"] = []
    first["results"][0]["output_hashes"] = {DIVISION_PATH: "a" * 64}
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"

    target = _evaluate(first, second)["targets"][0]

    assert target["normalized_exists"] is False
    assert target["qa_ok"] is False
    assert target["complete_ok"] is False
    assert target["failed_gates"] == ["normalized_exists", "qa_ok"]


def test_report_must_match_supplied_manifest_hash() -> None:
    first = _report()
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"
    first["manifest_sha256"] = "f" * 64
    second["manifest_sha256"] = "f" * 64

    with pytest.raises(CompletionManifestError, match="manifest_sha256 does not match"):
        _evaluate(first, second)
