#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_fac_001_dispatch.json")
FIXTURE_SCHEMA = Path("schemas/orch-fac-worker-dispatch.schema.json")
REPORT_SCHEMA = Path("schemas/orch-fac-001-report.schema.json")
NONWRITING = {"READ_ONLY", "HOLD", "BLOCKED", "NOT_HELD", "RELEASED"}


def canonical_hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def overlaps(a, b):
    return bool(set(a) & set(b))


def qa_status(checks):
    statuses = [row["status"] for row in checks]
    return "FAIL" if "FAIL" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"


def rel_transition(status):
    return {
        "PASS": ("READY", True, "RELEASED", "COMPLETED — QA PASS / PROMOTION READY", "QA-00"),
        "REVIEW": ("QUEUED", False, "HOLD", "REVIEW — EXCEPTION QUEUED", "EXCEPTION-QUEUE"),
        "FAIL": ("BLOCKED", False, "BLOCKED", "BLOCKED — REMEDIATION REQUIRED", "REMEDIATION"),
    }[status]


def reject(reasons, reason):
    reasons.append(reason)


def assert_registry(case_id, registry):
    held = [row for row in registry if row["lock_state"] == "HELD"]
    for row in registry:
        if row["lock_state"] == "HELD":
            assert row["lock_owner"] == row["conversation_id"], f"{case_id}: held-owner mismatch"
        if row["lock_state"] in NONWRITING:
            assert row["lock_owner"] == "NONE", f"{case_id}: nonwriting row retains owner"
    assert len({row["task_id"] for row in held}) == len(held), f"{case_id}: duplicate held task"
    assert len({row["lock_owner"] for row in held}) == len(held), f"{case_id}: owner holds multiple locks"
    for index, left in enumerate(held):
        for right in held[index + 1:]:
            assert not overlaps(left["write_surface"], right["write_surface"]), (
                f"{case_id}: overlapping held surfaces"
            )
    return len(held)


def run_case(case):
    registry = copy.deepcopy(case["initial_registry"])
    reasons = []
    peak_held = assert_registry(case["case_id"], registry)
    final_status = "PASS"
    promotion_status = "READY"
    promotion_eligible = True
    terminal_row = None

    for action in case["actions"]:
        cid = action["conversation_id"]
        task_id = action["task_id"]

        if action["type"] == "claim":
            surface = action["write_surface"]
            existing_owner_row = next(
                (row for row in registry if row["conversation_id"] == cid), None
            )
            held_rows = [row for row in registry if row["lock_state"] == "HELD"]

            if existing_owner_row and existing_owner_row["lock_state"] in NONWRITING:
                reject(reasons, "NONWRITING_OWNER")
                final_status = "REVIEW"
            elif any(row["lock_owner"] == cid for row in held_rows):
                reject(reasons, "OWNER_ALREADY_HELD")
            elif any(row["task_id"] == task_id for row in held_rows):
                reject(reasons, "TASK_ALREADY_HELD")
            elif any(overlaps(row["write_surface"], surface) for row in held_rows):
                reject(reasons, "SURFACE_CONFLICT")
            else:
                terminal_row = {
                    "conversation_id": cid,
                    "task_id": task_id,
                    "write_surface": surface,
                    "status": "ACTIVE — LOCK HELD",
                    "lock_state": "HELD",
                    "lock_owner": cid,
                    "handoff_to": "",
                }
                registry.append(terminal_row)
                assert terminal_row["lock_owner"] == cid
                assert terminal_row["lock_state"] == "HELD"

        else:
            terminal_row = next(
                (
                    row for row in registry
                    if row["conversation_id"] == cid and row["task_id"] == task_id
                ),
                None,
            )
            assert terminal_row is not None, f"{case['case_id']}: completion row missing"
            assert terminal_row["lock_state"] == "HELD", (
                f"{case['case_id']}: completion without held lock"
            )
            assert terminal_row["lock_owner"] == cid, (
                f"{case['case_id']}: completion by non-owner"
            )

            final_status = qa_status(action["qa_checks"])
            (
                promotion_status,
                promotion_eligible,
                lock_state,
                row_status,
                allowed_handoff,
            ) = rel_transition(final_status)
            assert action["handoff_to"] == allowed_handoff, (
                f"{case['case_id']}: illegal handoff for {final_status}"
            )

            terminal_row["lock_state"] = lock_state
            terminal_row["lock_owner"] = "NONE"
            terminal_row["status"] = row_status
            terminal_row["handoff_to"] = action["handoff_to"]

        peak_held = max(peak_held, assert_registry(case["case_id"], registry))

    if terminal_row is None:
        cid = case["actions"][-1]["conversation_id"]
        terminal_row = next(row for row in registry if row["conversation_id"] == cid)

    if final_status == "REVIEW" and terminal_row["lock_state"] == "READ_ONLY":
        promotion_status, promotion_eligible = "QUEUED", False

    held_locks = assert_registry(case["case_id"], registry)
    result = {
        "case_id": case["case_id"],
        "final_status": final_status,
        "promotion_status": promotion_status,
        "promotion_eligible": promotion_eligible,
        "final_lock_state": terminal_row["lock_state"],
        "held_locks": held_locks,
        "peak_held_locks": peak_held,
        "rejected_claims": len(reasons),
        "rejection_reasons": reasons,
        "handoff_to": terminal_row["handoff_to"],
    }

    for key, expected in case["expected"].items():
        assert result[key] == expected, (
            f"{case['case_id']} {key}: got {result[key]!r}, expected {expected!r}"
        )
    assert held_locks == 0, f"{case['case_id']}: terminal lock remains held"
    return result


def validate(schema_path, payload):
    schema = json.loads(schema_path.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert not errors, "\n".join(error.message for error in errors)


def main():
    data = json.loads(FIXTURE.read_text())
    validate(FIXTURE_SCHEMA, data)

    first = [run_case(case) for case in data["cases"]]
    second = [run_case(case) for case in data["cases"]]
    digest = canonical_hash(first)
    assert digest == canonical_hash(second), "dispatcher report is not deterministic"

    output = {
        "schema_version": 1,
        "gate_id": "ORCH-FAC-001",
        "status": "PASS",
        "deterministic": True,
        "fixture_sha256": file_hash(FIXTURE),
        "results": first,
        "report_sha256": digest,
    }
    validate(REPORT_SCHEMA, output)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
