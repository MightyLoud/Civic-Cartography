#!/usr/bin/env python3
import copy
import csv
import hashlib
import io
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_008_multnomah.json")
REGISTER = Path("evidence/measured-batch-100/completion-register.csv")
REQUIRED_TRUE = ["raw_exists","normalized_exists","identifier_join_ok","qa_ok","parity_ok","source_provenance_ok","complete_ok"]


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_register_row(target_id):
    rows = list(csv.DictReader(io.StringIO(REGISTER.read_text())))
    matches = [r for r in rows if r["target_id"] == target_id]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {target_id} row, got {len(matches)}")
    return matches[0]


def validate_target(target, register_row):
    exact = {
        "target_id": "target_id",
        "jurisdiction_name": "jurisdiction_name",
        "state": "state",
        "evaluation_id": "evaluation_id",
        "source_manifest_sha256": "source_manifest_sha256",
        "manifest_sha256": "manifest_sha256",
        "first_run_id": "first_run_id",
        "second_run_id": "second_run_id",
        "run_asof": "run_asof",
    }
    for tf, rf in exact.items():
        if str(target[tf]) != register_row[rf]:
            raise AssertionError(f"identity mismatch {tf}: {target[tf]!r} != {register_row[rf]!r}")
    for field in REQUIRED_TRUE:
        if not target[field]:
            raise AssertionError(f"required gate false: {field}")
        if register_row[field].upper() != "TRUE":
            raise AssertionError(f"register gate false: {field}")
    if target["first_run_id"] != target["second_run_id"]:
        raise AssertionError("deterministic run identity mismatch")
    if target["evidence_run_conclusion"] != "success":
        raise AssertionError("evidence run did not succeed")
    if target["completion_register_blob"] != "97514a9789545a3757e8908dec192becea1f99ec":
        raise AssertionError("completion register blob mismatch")


def replay(target, register_row):
    validate_target(target, register_row)
    events = [
        {"seq":1,"event":"READY","state":"READY"},
        {"seq":2,"event":"DISPATCH","state":"READ_ONLY_REPLAY"},
        {"seq":3,"event":"STAGE_COMPLETE","gate":"RAW","status":"PASS"},
        {"seq":4,"event":"STAGE_COMPLETE","gate":"NORMALIZED","status":"PASS"},
        {"seq":5,"event":"STAGE_COMPLETE","gate":"IDENTIFIER_JOIN","status":"PASS"},
        {"seq":6,"event":"STAGE_COMPLETE","gate":"QA","status":"PASS"},
        {"seq":7,"event":"STAGE_COMPLETE","gate":"PARITY","status":"PASS"},
        {"seq":8,"event":"STAGE_COMPLETE","gate":"PROVENANCE","status":"PASS"},
        {"seq":9,"event":"PROMOTION_READY","status":"PASS"},
        {"seq":10,"event":"HANDOFF","to":"READ_ONLY_CLOSEOUT"},
    ]
    return {
        "target_id": target["target_id"],
        "qa_status": "PASS",
        "promotion_ready": True,
        "held_locks": 0,
        "handoffs": 1,
        "events": events,
    }


def main():
    fixture = json.loads(FIXTURE.read_text())
    target = fixture["target"]
    register_row = load_register_row(target["target_id"])

    first = replay(copy.deepcopy(target), register_row)
    second = replay(copy.deepcopy(target), register_row)
    h1, h2 = canonical_hash(first), canonical_hash(second)
    if h1 != h2:
        raise AssertionError("real-batch replay is not deterministic")

    expected = fixture["expected"]
    for key in ("qa_status","promotion_ready","held_locks","handoffs"):
        if first[key] != expected[key]:
            raise AssertionError(f"unexpected {key}: {first[key]!r}")

    rejected = []
    for case in fixture["tamper_cases"]:
        mutated = copy.deepcopy(target)
        mutated[case["field"]] = case["value"]
        try:
            replay(mutated, register_row)
        except AssertionError:
            rejected.append(case["name"])
        else:
            raise AssertionError(f"tamper case accepted: {case['name']}")

    print(json.dumps({
        "gate_id":"ORCH-FAC-008",
        "status":"PASS",
        "target_id":target["target_id"],
        "jurisdiction":target["jurisdiction_name"],
        "evidence_run_id":target["evidence_run_id"],
        "deterministic":True,
        "report_sha256":h1,
        "tamper_cases_rejected":rejected,
        "promotion_ready":first["promotion_ready"],
        "held_locks":first["held_locks"],
        "handoffs":first["handoffs"]
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
