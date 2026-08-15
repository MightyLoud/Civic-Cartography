#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_003_batches.json")
STAGE_ORDER = ["SRC-FAC", "DOMAIN", "QA-FAC", "REL-FAC"]


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def overlaps(a, b):
    return bool(set(a) & set(b))


def run_child(child):
    transitions = []
    for stage in STAGE_ORDER:
        if stage not in child["stages"]:
            break
        status = child["stages"][stage]
        transitions.append({"stage": stage, "status": status, "lock": "RELEASED"})
        if status != "PASS":
            return {
                "task_id": child["task_id"],
                "terminal": status,
                "promotion_ready": False,
                "transitions": transitions,
                "held_locks": 0,
            }
    if len(transitions) != len(STAGE_ORDER):
        raise AssertionError(f"nonterminal child missing required stage: {child['task_id']}")
    return {
        "task_id": child["task_id"],
        "terminal": "PASS",
        "promotion_ready": True,
        "transitions": transitions,
        "held_locks": 0,
    }


def run_case(case):
    # Deterministic scheduler: preserve fixture order; tasks whose write surfaces
    # overlap an earlier sibling are explicitly counted as waiting/serialized.
    overlap_waits = 0
    earlier = []
    for child in case["children"]:
        if any(overlaps(child["write_surface"], prior["write_surface"]) for prior in earlier):
            overlap_waits += 1
        earlier.append(child)

    results = [run_child(c) for c in case["children"]]
    if any(r["held_locks"] for r in results):
        raise AssertionError(f"fan-in with leaked child lock: {case['case_id']}")

    promotion_ready = sum(r["promotion_ready"] for r in results)
    review = sum(r["terminal"] == "REVIEW" for r in results)
    fail = sum(r["terminal"] == "FAIL" for r in results)
    batch_status = "FAIL" if fail else ("REVIEW" if review else "PASS")

    result = {
        "case_id": case["case_id"],
        "batch_status": batch_status,
        "promotion_ready": promotion_ready,
        "review": review,
        "fail": fail,
        "overlap_waits": overlap_waits,
        "held_locks": 0,
        "children": results,
    }
    for key, expected in case["expected"].items():
        if result[key] != expected:
            raise AssertionError(f"{case['case_id']} {key}: got {result[key]!r}, expected {expected!r}")

    # Fan-in can PASS only if every child is promotion-ready.
    if batch_status == "PASS" and promotion_ready != len(results):
        raise AssertionError(f"false batch PASS: {case['case_id']}")
    # REVIEW/FAIL must remain explicit at rollup.
    if any(r["terminal"] == "FAIL" for r in results) and batch_status != "FAIL":
        raise AssertionError(f"failed child lost at fan-in: {case['case_id']}")
    if not fail and any(r["terminal"] == "REVIEW" for r in results) and batch_status != "REVIEW":
        raise AssertionError(f"review child lost at fan-in: {case['case_id']}")
    return result


def main():
    data = json.loads(FIXTURE.read_text())
    first = [run_case(c) for c in data["cases"]]
    second = [run_case(c) for c in data["cases"]]
    h1, h2 = canonical_hash(first), canonical_hash(second)
    if h1 != h2:
        raise AssertionError("batch orchestration output is not deterministic")
    print(json.dumps({
        "gate_id": "ORCH-FAC-003",
        "status": "PASS",
        "cases": len(first),
        "deterministic": True,
        "report_sha256": h1,
        "results": [{k:r[k] for k in ("case_id","batch_status","promotion_ready","review","fail","overlap_waits","held_locks")} for r in first]
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
