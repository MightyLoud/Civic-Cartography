#!/usr/bin/env python3
"""Aggregate ORCH-PROD-001 closeout reconciliation."""
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_prod_001_closeout.json")
FIXTURE_SCHEMA = Path("schemas/orch-prod-001-closeout.schema.json")
REPORT_SCHEMA = Path("schemas/orch-prod-001-report.schema.json")
ZERO_HASH = "0" * 64
EXPECTED = [
    ("OR-PB03-001", "Baker County", "41001", 458),
    ("OR-PB03-002", "Benton County", "41003", 459),
    ("OR-PB03-003", "Clackamas County", "41005", 460),
]
KNOWN_EVIDENCE = {
    "OR-PB03-001": (31989075122, 95269155928, "147bf699bde562f4a6c1", "17dc286c0b6a5bd0858188721f33fc1b866f14dde04ff8a8ac5f340e01cfe794"),
    "OR-PB03-002": (31992029955, 95277173414, "ef7b94f40587e24bf517", "28cfe25843e58622b1e6dafc919367ab0d85da3d633aeede095200bc3cbd49a6"),
    "OR-PB03-003": (31992370600, 95278072027, "6b55416ff61f70ae2ed8", "6c3fb7a59d4e1a44584f56c6fea99a986d580bfd8c103b4b2cd9e9f6226b4287"),
}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def add_event(events, task, kind, previous_state, next_state, actor, surface):
    seq = len(events) + 1
    event = {
        "event_id": f"{task['target_id']}:{seq:02d}",
        "idempotency_key": f"ORCH-PROD-001:{task['workflow_run_id']}:{seq:02d}",
        "task_id": task["target_id"],
        "seq": seq,
        "event_type": kind,
        "previous_state": previous_state,
        "next_state": next_state,
        "context": {
            "conversation_id": "issue-457",
            "actor": actor,
            "gate_id": "ORCH-PROD-001",
            "write_surface": [surface],
        },
    }
    event["previous_event_hash"] = events[-1]["event_hash"] if events else ZERO_HASH
    event["event_hash"] = digest(event)
    events.append(event)


def trace_task(task):
    events = []
    add_event(events, task, "READY", "BLOCKED", "READY", "ORCH", "authority:read-only")
    add_event(events, task, "DISPATCH", "READY", "DISPATCHED", "ORCH", "production:bounded")
    add_event(events, task, "LOCK_ACQUIRED", "DISPATCHED", "ACTIVE", "PROD-WORKER", task["target_id"])
    for surface in ("source-input", "nat-fac-generation", "qa-parity-evidence"):
        add_event(events, task, "STAGE_START", "ACTIVE", "ACTIVE", "PROD-WORKER", surface)
        add_event(events, task, "STAGE_COMPLETE", "ACTIVE", "ACTIVE", "PROD-WORKER", surface)
    add_event(events, task, "PROMOTION_READY", "ACTIVE", "READY_FOR_HANDOFF", "REL-FAC", "promotion:internal")
    add_event(events, task, "HANDOFF", "READY_FOR_HANDOFF", "COMPLETED", "ORCH", "handoff:internal")
    add_event(events, task, "LOCK_RELEASED", "COMPLETED", "COMPLETED", "PROD-WORKER", task["target_id"])
    return events


def validate_trace(events):
    previous, state, held, handoffs = ZERO_HASH, "BLOCKED", 0, 0
    for seq, event in enumerate(events, 1):
        if event["seq"] != seq or event["previous_event_hash"] != previous:
            raise ValueError("event sequence/hash-chain break")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        if event["event_hash"] != digest(body):
            raise ValueError("event payload tamper")
        if event["previous_state"] != state:
            raise ValueError("illegal task transition")
        kind = event["event_type"]
        if kind == "LOCK_ACQUIRED":
            held += 1
        elif kind in {"STAGE_START", "STAGE_COMPLETE", "PROMOTION_READY"} and held != 1:
            raise ValueError("mutating event without exactly one lock")
        elif kind == "HANDOFF":
            handoffs += 1
        elif kind == "LOCK_RELEASED":
            if held != 1:
                raise ValueError("lock release without lock")
            held -= 1
        if held > 1:
            raise ValueError("capacity exceeded")
        state = event["next_state"]
        previous = event["event_hash"]
    if state != "COMPLETED" or held != 0 or handoffs != 1:
        raise ValueError("invalid terminal task disposition")
    return {"held_locks": held, "handoffs": handoffs}


def reconcile(data):
    if data["capacity"] != 1 or data["automatic_retries"] or data["public_release"]:
        raise ValueError("unsafe batch controls")
    tasks = sorted(data["tasks"], key=lambda item: item["sequence"])
    traces, results, predecessor_merge = [], [], None
    active = 0
    for index, (task, identity) in enumerate(zip(tasks, EXPECTED), 1):
        if (task["target_id"], task["county"], task["geoid"], task["pr"]) != identity or task["sequence"] != index:
            raise ValueError("governed identity/order mismatch")
        if predecessor_merge is not None and task["base_sha"] != predecessor_merge:
            raise ValueError("successor ancestry bypassed predecessor merge")
        if index > 1 and tasks[index - 2]["status"] != "PASS":
            raise ValueError("successor activated after non-PASS predecessor")
        required = ("production_acceptance", "deterministic", "nesting_parity", "enrichment_guard")
        if task["status"] != "PASS" or not all(task[field] for field in required):
            raise ValueError("production evidence did not pass")
        observed = (task["workflow_run_id"], task["job_id"], task["production_run_id"], task["artifact_sha256"])
        if observed != KNOWN_EVIDENCE[task["target_id"]]:
            raise ValueError("exact run/job/production/artifact evidence mismatch")
        if task["head_sha"] == task["merge_sha"]:
            raise ValueError("invalid commit identity")
        active += 1
        if active > data["capacity"]:
            raise ValueError("capacity exceeded")
        events = trace_task(task)
        terminal = validate_trace(events)
        active -= 1
        traces.extend(events)
        results.append({
            "sequence": index, "target_id": task["target_id"], "status": "PASS",
            "workflow_run_id": task["workflow_run_id"], "job_id": task["job_id"],
            "production_run_id": task["production_run_id"],
            "artifact_sha256": task["artifact_sha256"], **terminal,
        })
        predecessor_merge = task["merge_sha"]
    return results, traces


def rejected(fn):
    try:
        fn()
    except (ValueError, AssertionError):
        return "REJECTED"
    raise AssertionError("negative probe accepted")


def changed(data, task_index, field, value):
    mutation = copy.deepcopy(data)
    mutation["tasks"][task_index][field] = value
    return mutation


def main():
    data = json.loads(FIXTURE.read_text())
    Draft202012Validator(json.loads(FIXTURE_SCHEMA.read_text())).validate(data)
    results, traces = reconcile(data)
    second_results, second_traces = reconcile(copy.deepcopy(data))
    if canonical_bytes((results, traces)) != canonical_bytes((second_results, second_traces)):
        raise AssertionError("aggregate replay not deterministic")

    probes = {
        "review_blocks_successor": rejected(lambda: reconcile(changed(data, 0, "status", "REVIEW"))),
        "fail_blocks_successor": rejected(lambda: reconcile(changed(data, 1, "status", "FAIL"))),
        "ancestry_break": rejected(lambda: reconcile(changed(data, 2, "base_sha", "0" * 40))),
        "determinism_false": rejected(lambda: reconcile(changed(data, 1, "deterministic", False))),
        "parity_false": rejected(lambda: reconcile(changed(data, 2, "nesting_parity", False))),
        "enrichment_false": rejected(lambda: reconcile(changed(data, 0, "enrichment_guard", False))),
        "artifact_identity": rejected(lambda: reconcile(changed(data, 0, "artifact_sha256", "0" * 64))),
        "capacity": rejected(lambda: reconcile({**copy.deepcopy(data), "capacity": 2})),
        "automatic_retry": rejected(lambda: reconcile({**copy.deepcopy(data), "automatic_retries": True})),
        "public_release": rejected(lambda: reconcile({**copy.deepcopy(data), "public_release": True})),
    }
    core = {
        "gate_id": "ORCH-PROD-001", "status": "PASS", "capacity": 1,
        "tasks": results, "serial_order_verified": True, "fail_closed_verified": True,
        "max_held_locks": 1, "held_locks": sum(item["held_locks"] for item in results),
        "handoffs": sum(item["handoffs"] for item in results),
        "event_trace_sha256": digest(traces), "deterministic": True,
        "tamper_probes": probes,
    }
    report = {**core, "report_sha256": digest(core)}
    Draft202012Validator(json.loads(REPORT_SCHEMA.read_text())).validate(report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
