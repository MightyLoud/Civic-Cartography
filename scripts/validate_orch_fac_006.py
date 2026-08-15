#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_006_scheduler.json")


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def overlaps(a, b):
    return bool(set(a) & set(b))


def schedule(tasks, capacity, aging_step):
    ready = []
    for t in tasks:
        if t["state"] != "READY":
            continue
        effective = t["priority"] + t["wait"] * aging_step
        ready.append(( -effective, t["task_id"], t ))
    ready.sort(key=lambda x: (x[0], x[1]))

    selected = []
    surfaces = []
    for _, _, task in ready:
        if len(selected) >= capacity:
            break
        if any(overlaps(task["write_surface"], s) for s in surfaces):
            continue
        selected.append(task["task_id"])
        surfaces.append(task["write_surface"])
    return selected


def run_case(case, aging_step):
    if case.get("complete_then_reschedule"):
        tasks = [dict(t) for t in case["tasks"]]
        rounds = []
        while True:
            chosen = schedule(tasks, case["capacity"], aging_step)
            if not chosen:
                break
            rounds.append(chosen)
            chosen_set = set(chosen)
            for t in tasks:
                if t["task_id"] in chosen_set:
                    t["state"] = "PASS"
            if not any(t["state"] == "READY" for t in tasks):
                break
        if rounds != case["expected_rounds"]:
            raise AssertionError(f"{case['case_id']} rounds: got {rounds}, expected {case['expected_rounds']}")
        return {"case_id":case["case_id"],"rounds":rounds}

    selected = schedule(case["tasks"], case["capacity"], aging_step)
    if selected != case["expected_selected"]:
        raise AssertionError(f"{case['case_id']}: got {selected}, expected {case['expected_selected']}")
    if len(selected) > case["capacity"]:
        raise AssertionError(f"capacity exceeded: {case['case_id']}")
    return {"case_id":case["case_id"],"selected":selected}


def main():
    data = json.loads(FIXTURE.read_text())
    first = [run_case(c, data["aging_step"]) for c in data["cases"]]
    second = [run_case(c, data["aging_step"]) for c in data["cases"]]
    h1, h2 = canonical_hash(first), canonical_hash(second)
    if h1 != h2:
        raise AssertionError("scheduler output is not deterministic")
    print(json.dumps({
        "gate_id":"ORCH-FAC-006",
        "status":"PASS",
        "cases":len(first),
        "deterministic":True,
        "report_sha256":h1,
        "results":first
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
