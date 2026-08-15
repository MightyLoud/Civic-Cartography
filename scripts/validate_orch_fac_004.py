#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_004_recovery.json")
STAGE_ORDER = ["SRC-FAC", "DOMAIN", "QA-FAC", "REL-FAC"]


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def stage_write(stage, task_id):
    return f"{stage.lower()}:{task_id}"


def run_case(case):
    state = copy.deepcopy(case["initial"])
    state.setdefault("handoffs", 0)
    state.setdefault("exceptions", 0)
    recovery = case["recovery"]

    # Terminal replay is an idempotent no-op.
    if state.get("terminal") in {"PASS", "REVIEW", "FAIL"}:
        result = {
            "case_id": case["case_id"],
            "terminal": state["terminal"],
            "retry_count": state["retry_count"],
            "writes": len(state["writes"]),
            "handoffs": state.get("handoffs", 0),
            "exceptions": state.get("exceptions", 0),
            "held_locks": 0,
        }
        return result

    # Recovery must be explicit and must reclaim/release any prior lock before ownership changes.
    if not recovery.get("reason") or not recovery.get("new_owner"):
        raise AssertionError(f"implicit recovery forbidden: {case['case_id']}")
    state["lock_state"] = "HELD"
    state["lock_owner"] = recovery["new_owner"]
    state["retry_count"] += 1

    completed = set(state.get("completed_stages", []))
    writes = set(state.get("writes", []))
    terminal = None

    for stage in STAGE_ORDER:
        if stage in completed:
            continue
        if stage not in recovery["remaining_stages"]:
            continue
        status = recovery["remaining_stages"][stage]
        write_key = stage_write(stage, case["task_id"])
        # Idempotency: stage output is applied once even if retry input repeats it.
        writes.add(write_key)
        completed.add(stage)
        if status == "REVIEW":
            terminal = "REVIEW"
            state["exceptions"] = 1
            break
        if status == "FAIL":
            terminal = "FAIL"
            state["exceptions"] = 1
            break

    if terminal is None:
        terminal = "PASS" if all(s in completed for s in STAGE_ORDER) else None

    state["completed_stages"] = sorted(completed, key=STAGE_ORDER.index)
    state["writes"] = sorted(writes)
    state["terminal"] = terminal
    state["lock_state"] = "RELEASED" if terminal == "PASS" else ("HOLD" if terminal == "REVIEW" else "BLOCKED")
    state["lock_owner"] = "NONE"
    if terminal == "PASS":
        state["handoffs"] = 1
    elif terminal in {"REVIEW", "FAIL"}:
        state["handoffs"] = 0

    result = {
        "case_id": case["case_id"],
        "terminal": terminal,
        "retry_count": state["retry_count"],
        "writes": len(state["writes"]),
        "handoffs": state.get("handoffs", 0),
        "exceptions": state.get("exceptions", 0),
        "held_locks": 1 if state["lock_state"] == "HELD" else 0,
    }
    for key, expected in case["expected"].items():
        if result[key] != expected:
            raise AssertionError(f"{case['case_id']} {key}: got {result[key]!r}, expected {expected!r}")
    if terminal == "PASS" and result["handoffs"] != 1:
        raise AssertionError(f"PASS must produce exactly one handoff: {case['case_id']}")
    if terminal in {"REVIEW", "FAIL"} and result["exceptions"] != 1:
        raise AssertionError(f"non-PASS must produce exactly one exception: {case['case_id']}")
    if result["held_locks"]:
        raise AssertionError(f"recovery leaked lock: {case['case_id']}")
    return result


def main():
    data = json.loads(FIXTURE.read_text())
    first = [run_case(c) for c in data["cases"]]
    second = [run_case(c) for c in data["cases"]]
    h1, h2 = canonical_hash(first), canonical_hash(second)
    if h1 != h2:
        raise AssertionError("recovery output is not deterministic")
    print(json.dumps({
        "gate_id": "ORCH-FAC-004",
        "status": "PASS",
        "cases": len(first),
        "deterministic": True,
        "report_sha256": h1,
        "results": first,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
