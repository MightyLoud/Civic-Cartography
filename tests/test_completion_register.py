from __future__ import annotations

import csv

from civic_cartography.completion_register import (
    REGISTER_FIELDS,
    upsert_completion_register,
)


def _completion_manifest(*, complete: bool = True) -> dict:
    gates = {
        "raw_exists": complete,
        "normalized_exists": complete,
        "identifier_join_ok": complete,
        "qa_ok": complete,
        "parity_ok": complete,
        "source_provenance_ok": complete,
    }
    return {
        "schema_version": 1,
        "evaluation_id": "eval-001",
        "source_manifest_sha256": "a" * 64,
        "manifest_sha256": "b" * 64,
        "first_run_id": "run-1",
        "second_run_id": "run-2",
        "run_asof": "2026-08-08T03:30:00Z",
        "targets": [
            {
                "target_id": "MB100-041",
                "jurisdiction_name": "Example District",
                "state": "il",
                **gates,
                "complete_ok": complete,
                "confidence": "HIGH" if complete else "UNVERIFIED",
                "failed_gates": [] if complete else list(gates),
            }
        ],
    }


def test_register_projects_machine_gates_for_sheets(tmp_path) -> None:
    path = tmp_path / "completion-register.csv"
    rows = upsert_completion_register(
        _completion_manifest(),
        register_path=path,
        evidence_ref="evidence/mb100-041/completion-manifest.json",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["target_id"] == "MB100-041"
    assert row["raw_exists"] == "TRUE"
    assert row["normalized_exists"] == "TRUE"
    assert row["identifier_join_ok"] == "TRUE"
    assert row["qa_ok"] == "TRUE"
    assert row["parity_ok"] == "TRUE"
    assert row["source_provenance_ok"] == "TRUE"
    assert row["complete_ok"] == "TRUE"
    assert row["confidence"] == "HIGH"

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == REGISTER_FIELDS
        assert list(reader)[0]["evidence_ref"].endswith("completion-manifest.json")


def test_register_upsert_is_idempotent_and_target_keyed(tmp_path) -> None:
    path = tmp_path / "completion-register.csv"
    upsert_completion_register(
        _completion_manifest(), register_path=path, evidence_ref="first.json"
    )
    rows = upsert_completion_register(
        _completion_manifest(complete=False),
        register_path=path,
        evidence_ref="second.json",
    )

    assert len(rows) == 1
    assert rows[0]["target_id"] == "MB100-041"
    assert rows[0]["complete_ok"] == "FALSE"
    assert rows[0]["confidence"] == "UNVERIFIED"
    assert rows[0]["evidence_ref"] == "second.json"
    assert "raw_exists" in rows[0]["failed_gates"]
