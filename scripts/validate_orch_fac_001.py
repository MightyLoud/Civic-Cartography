#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_001_dispatch.json")
NONWRITING = {"READ_ONLY", "HOLD", "BLOCKED", "NOT_HELD", "RELEASED"}


def canonical_hash(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def overlaps(a, b):
    return bool(set(a) & set(b))


def run_case(case):
    registry = copy.deepcopy(case["initial_registry"])
    rejected = 0
    final_status = "PASS"

    for action in case["actions"]:
        if action["type"] == "claim":
            cid = action["conversation_id"]
            surface = action.get("write_surface", [])

            existing = next((r for r in registry if r["conversation_id"] == cid), None)
            if existing and existing["lock_state"] in NONWRITING:
                rejected += 1
                final_status = "REVIEW"
                continue

            conflict = any(
                r["lock_state"] == "HELD"
                and r["lock_owner"] != cid
                and overlaps(r["write_surface"], surface)
                for r in registry
            )
            if conflict:
                rejected += 1
                continue

            registry.append({
                "conversation_id": cid,
                "task_id": action["task_id"],
                "write_surface": surface,
                "status": "ACTIVE",
                "lock_state": "HELD",
                "lock_owner": cid,
                "handoff_to": ""
            })

        elif action["type"] == "complete":
            cid = action["conversation_id"]
            row = next((r for r in registry if r["conversation_id"] == cid and r["task_id"] == action["task_id"]), None)
            if not row or row["lock_state"] != "HELD" or row["lock_owner"] != cid:
                raise AssertionError(f"completion without valid held lock: {case['case_id']} {cid}")

            qa = action["qa_status"]
            final_status = qa
            row["lock_state"] = "RELEASED" if qa == "PASS" else ("HOLD" if qa == "REVIEW" else "BLOCKED")
            row["lock_owner"] = "NONE"
            row["status"] = {
                "PASS": "COMPLETED — READY FOR QA/HANDOFF",
                "REVIEW": "REVIEW — EXCEPTION QUEUED",
                "FAIL": "BLOCKED — REMEDIATION REQUIRED"
            }[qa]
            row["handoff_to"] = action.get("handoff_to", "")

    held = sum(1 for r in registry if r["lock_state"] == "HELD")
    result = {
        "case_id": case["case_id"],
        "final_status": final_status,
        "held_locks": held,
        "rejected_claims": rejected,
        "registry": registry,
    }
    expected = case["expected"]
    for key in ("final_status", "held_locks", "rejected_claims"):
        if result[key] != expected[key]:
            raise AssertionError(f"{case['case_id']} {key}: got {result[key]!r}, expected {expected[key]!r}")

    # Global invariants.
    for row in registry:
        if row["lock_state"] == "HELD" and row["lock_owner"] != row["conversation_id"]:
            raise AssertionError(f"held lock owner mismatch: {case['case_id']}")
        if row["lock_state"] in NONWRITING and row["lock_owner"] not in {"", "NONE"}:
            raise AssertionError(f"nonwriting state retains owner: {case['case_id']}")

    held_rows = [r for r in registry if r["lock_state"] == "HELD"]
    for i, left in enumerate(held_rows):
        for right in held_rows[i + 1:]:
            if overlaps(left["write_surface"], right["write_surface"]):
                raise AssertionError(f"overlapping held surfaces: {case['case_id']}")

    return result


def main():
    data = json.loads(FIXTURE.read_text())
    first = [run_case(c) for c in data["cases"]]
    second = [run_case(c) for c in data["cases"]]
    h1 = canonical_hash(first)
    h2 = canonical_hash(second)
    if h1 != h2:
        raise AssertionError("dispatcher output is not deterministic")

    print(json.dumps({
        "gate_id": "ORCH-FAC-001",
        "status": "PASS",
        "cases": len(first),
        "deterministic": True,
        "report_sha256": h1,
        "results": [{k: r[k] for k in ("case_id", "final_status", "held_locks", "rejected_claims")} for r in first]
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
