#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_005_dag.json")
TERMINAL = {"PASS", "REVIEW", "FAIL"}


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def has_cycle(tasks):
    deps = {t["task_id"]: list(t["depends_on"]) for t in tasks}
    visiting, visited = set(), set()
    def visit(node):
        if node in visited:
            return False
        if node in visiting:
            return True
        visiting.add(node)
        for dep in deps.get(node, []):
            if dep not in deps:
                raise AssertionError(f"unknown dependency {dep} for {node}")
            if visit(dep):
                return True
        visiting.remove(node)
        visited.add(node)
        return False
    return any(visit(n) for n in deps)


def run_case(case):
    tasks = {t["task_id"]: dict(t) for t in case["tasks"]}
    cycle = has_cycle(case["tasks"])
    if cycle:
        result = {"case_id": case["case_id"], "cycle": True, "ready_order": [], "blocked": sorted(tasks)}
    else:
        completed = set()
        emitted = set()
        ready_order = []
        while True:
            ready = sorted(
                tid for tid, t in tasks.items()
                if tid not in emitted
                and all(dep in completed for dep in t["depends_on"])
            )
            if not ready:
                break
            ready_order.append(ready)
            for tid in ready:
                emitted.add(tid)
            for tid in ready:
                status = tasks[tid]["status"]
                if status == "PASS":
                    completed.add(tid)
                elif status in {"REVIEW", "FAIL", "PENDING"}:
                    pass
                else:
                    raise AssertionError(f"invalid status {status} for {tid}")

        # A task is blocked if it was never ready. REVIEW/FAIL tasks themselves were ready,
        # but their descendants remain blocked because only PASS satisfies dependencies.
        blocked = sorted(set(tasks) - emitted)
        result = {"case_id": case["case_id"], "cycle": False, "ready_order": ready_order, "blocked": blocked}

    expected = case["expected"]
    for key in ("cycle", "ready_order", "blocked"):
        if result[key] != expected[key]:
            raise AssertionError(f"{case['case_id']} {key}: got {result[key]!r}, expected {expected[key]!r}")
    return result


def main():
    data = json.loads(FIXTURE.read_text())
    first = [run_case(c) for c in data["cases"]]
    second = [run_case(c) for c in data["cases"]]
    h1, h2 = canonical_hash(first), canonical_hash(second)
    if h1 != h2:
        raise AssertionError("DAG scheduler output is not deterministic")
    print(json.dumps({
        "gate_id": "ORCH-FAC-005",
        "status": "PASS",
        "cases": len(first),
        "deterministic": True,
        "report_sha256": h1,
        "results": first,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
