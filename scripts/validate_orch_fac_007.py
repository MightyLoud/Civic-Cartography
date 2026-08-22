#!/usr/bin/env python3
"""Executable ORCH-FAC-007 append-only audit-log acceptance proof."""
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_fac_007_events.json")
EVENT_SCHEMA = Path("schemas/orch-fac-007-events.schema.json")
REPORT_SCHEMA = Path("schemas/orch-fac-007-report.schema.json")
ZERO_HASH = "0" * 64
PREREQUISITES = [f"ORCH-FAC-{number:03d}" for number in range(1, 7)]
EVENT_TYPES = {
    "READY", "DISPATCH", "LOCK_ACQUIRED", "STAGE_START", "STAGE_COMPLETE",
    "REVIEW", "FAIL", "RETRY", "LOCK_RELEASED", "PROMOTION_READY", "HANDOFF",
}
TRANSITIONS = {
    "READY": ("BLOCKED", "READY"),
    "DISPATCH": ("READY", "DISPATCHED"),
    "LOCK_ACQUIRED": ("DISPATCHED", "ACTIVE"),
    "STAGE_START": ("ACTIVE", "ACTIVE"),
    "STAGE_COMPLETE": ("ACTIVE", "ACTIVE"),
    "REVIEW": ("ACTIVE", "REVIEW"),
    "FAIL": ("ACTIVE", "FAIL"),
    "RETRY": ("FAIL", "READY"),
    "LOCK_RELEASED": None,
    "PROMOTION_READY": ("ACTIVE", "READY_FOR_HANDOFF"),
    "HANDOFF": ("READY_FOR_HANDOFF", "COMPLETED"),
}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def deduplicate(events):
    identities, keys, accepted = {}, {}, []
    suppressed = 0
    for event in events:
        payload = canonical_bytes(event)
        eid, key = event["event_id"], event["idempotency_key"]
        if eid in identities or key in keys:
            if identities.get(eid, payload) != payload or keys.get(key, payload) != payload:
                raise ValueError("identity/idempotency collision has conflicting payload")
            suppressed += 1
            continue
        identities[eid] = payload
        keys[key] = payload
        accepted.append(event)
    return accepted, suppressed


def materialize(events):
    chained, previous = [], {}
    for event in sorted(events, key=lambda item: (item["task_id"], item["seq"])):
        record = copy.deepcopy(event)
        record["previous_event_hash"] = previous.get(record["task_id"], ZERO_HASH)
        record["event_hash"] = digest(record)
        previous[record["task_id"]] = record["event_hash"]
        chained.append(record)
    return chained


def verify_chain(records):
    previous = {}
    for record in records:
        expected_previous = previous.get(record["task_id"], ZERO_HASH)
        if record["previous_event_hash"] != expected_previous:
            raise ValueError("broken append-only previous-event hash")
        body = {key: value for key, value in record.items() if key != "event_hash"}
        if record["event_hash"] != digest(body):
            raise ValueError("tampered event hash")
        previous[record["task_id"]] = record["event_hash"]


def replay(events, snapshots):
    accepted, suppressed = deduplicate(events)
    records = materialize(accepted)
    verify_chain(records)
    state = {}
    observed_types = set()
    last_seq = {}
    for record in records:
        task = record["task_id"]
        current = state.setdefault(task, {
            "task_id": task, "state": "BLOCKED", "lock_state": "RELEASED",
            "promotion_ready": False, "retry_count": 0, "stage_open": False,
        })
        expected_seq = last_seq.get(task, 0) + 1
        if record["seq"] != expected_seq:
            raise ValueError(f"{task}: non-monotonic or missing sequence")
        last_seq[task] = record["seq"]
        event_type = record["event_type"]
        observed_types.add(event_type)
        transition = TRANSITIONS[event_type]
        if transition is None:
            if record["previous_state"] != current["state"] or record["next_state"] != current["state"]:
                raise ValueError(f"{task}: lock release changed task state")
        elif (record["previous_state"], record["next_state"]) != transition or current["state"] != transition[0]:
            raise ValueError(f"{task}: illegal {event_type} transition")
        if event_type == "LOCK_ACQUIRED":
            if current["lock_state"] != "RELEASED":
                raise ValueError(f"{task}: lock acquired twice")
            current["lock_state"] = "HELD"
        elif event_type == "LOCK_RELEASED":
            if current["lock_state"] != "HELD" or current["stage_open"]:
                raise ValueError(f"{task}: illegal lock release")
            current["lock_state"] = "RELEASED"
        elif event_type == "STAGE_START":
            if current["lock_state"] != "HELD" or current["stage_open"]:
                raise ValueError(f"{task}: illegal stage start")
            current["stage_open"] = True
        elif event_type == "STAGE_COMPLETE":
            if current["lock_state"] != "HELD" or not current["stage_open"]:
                raise ValueError(f"{task}: stage complete without stage start")
            current["stage_open"] = False
        elif event_type in {"REVIEW", "FAIL"}:
            if current["lock_state"] != "HELD" or not current["stage_open"]:
                raise ValueError(f"{task}: terminal stage event without active stage")
            current["stage_open"] = False
        elif event_type == "RETRY":
            if current["lock_state"] != "RELEASED":
                raise ValueError(f"{task}: retry while locked")
            current["retry_count"] += 1
            current["promotion_ready"] = False
        elif event_type == "PROMOTION_READY":
            if current["lock_state"] != "HELD" or current["stage_open"]:
                raise ValueError(f"{task}: premature promotion")
            current["promotion_ready"] = True
        elif event_type == "HANDOFF":
            if current["lock_state"] != "RELEASED" or not current["promotion_ready"]:
                raise ValueError(f"{task}: handoff without released lock and promotion")
        if transition is not None:
            current["state"] = record["next_state"]

    actual = []
    for task in sorted(state):
        item = {key: value for key, value in state[task].items() if key != "stage_open"}
        actual.append(item)
    expected = sorted(snapshots, key=lambda item: item["task_id"])
    if actual != expected:
        raise ValueError(f"registry snapshot mismatch: {actual!r} != {expected!r}")
    return {
        "records": records, "snapshots": actual, "suppressed": suppressed,
        "event_types": sorted(observed_types),
    }


def rejected(fn):
    try:
        fn()
    except (ValueError, AssertionError):
        return "REJECTED"
    raise AssertionError("negative probe was incorrectly accepted")


def main():
    fixture = json.loads(FIXTURE.read_text())
    event_schema = json.loads(EVENT_SCHEMA.read_text())
    report_schema = json.loads(REPORT_SCHEMA.read_text())
    Draft202012Validator(event_schema).validate(fixture)

    events = [event for case in fixture["cases"] for event in case["events"]]
    snapshots = [case["registry_snapshot"] for case in fixture["cases"]]
    baseline = replay(events, snapshots)
    if set(baseline["event_types"]) != EVENT_TYPES:
        raise AssertionError("fixture does not cover every standardized event type")

    shuffled = [event for case in reversed(fixture["cases"]) for event in reversed(case["events"])]
    second = replay(shuffled, list(reversed(snapshots)))
    if digest(baseline["records"]) != digest(second["records"]):
        raise AssertionError("canonical replay is input-order dependent")

    missing = [event for event in events if not (
        event["task_id"] == "TASK-PASS" and event["event_type"] == "LOCK_RELEASED"
    )]
    illegal = copy.deepcopy(events)
    target = next(event for event in illegal if event["task_id"] == "TASK-PASS" and event["event_type"] == "STAGE_START")
    target["previous_state"] = "READY"
    conflict = copy.deepcopy(events)
    duplicate = copy.deepcopy(next(event for event in events if event["event_id"] == "pass-e5"))
    duplicate["context"]["actor"] = "CONFLICTING-ACTOR"
    conflict.append(duplicate)
    tampered_records = copy.deepcopy(baseline["records"])
    tampered_records[0]["context"]["actor"] = "TAMPERED"

    core = {
        "gate_id": "ORCH-FAC-007",
        "status": "PASS",
        "prerequisites": PREREQUISITES,
        "canonical_order": True,
        "hash_chain_verified": True,
        "deterministic": True,
        "duplicate_events_suppressed": baseline["suppressed"],
        "event_types_covered": baseline["event_types"],
        "tamper_probes": {
            "missing_event": rejected(lambda: replay(missing, snapshots)),
            "illegal_transition": rejected(lambda: replay(illegal, snapshots)),
            "conflicting_duplicate": rejected(lambda: replay(conflict, snapshots)),
            "hash_tamper": rejected(lambda: verify_chain(tampered_records)),
        },
        "registry_snapshots": baseline["snapshots"],
    }
    report = {**core, "report_sha256": digest(core)}
    Draft202012Validator(report_schema).validate(report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
