#!/usr/bin/env python3
"""Aggregate ORCH-PROD-002 capacity-2 DAG closeout reconciliation."""
import copy
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_prod_002_closeout.json")
FIXTURE_SCHEMA = Path("schemas/orch-prod-002-closeout.schema.json")
REPORT_SCHEMA = Path("schemas/orch-prod-002-report.schema.json")
ZERO = "0" * 64
EXPECTED_TASKS = {
    "OR-PB04-001": ("Clatsop County", "41007", [], 31993798389, 95281803891, "df01ac52f1a3d118dd8d", "3b9b31e6fb13879b07778c4d9b3da580ebff2c7009a881b6c5962e9df2bf973b"),
    "OR-PB04-002": ("Columbia County", "41009", [], 31993798389, 95281803898, "6734a88bc06de2de9bfc", "cc4c5833bdc0433c92ac41638b16453535c1f7cd2e52627444d029e7ff4e45e3"),
    "OR-PB04-003": ("Coos County", "41011", ["OR-PB04-001"], 31994616230, 95283957637, "929374d137a3e31e7e68", "f299e13e87627b4450ec5626089c59f232c4cf43e8c93145b146e5daae9f1985"),
    "OR-PB04-004": ("Crook County", "41013", ["OR-PB04-002"], 31994616230, 95283957638, "77ed654d6ab8d27328ea", "842835f3c3dc7b60eb39dd517d8bf51e97e19b948bb12148e2c6ad7bad0f3c91"),
    "OR-PB04-005": ("Curry County", "41015", ["OR-PB04-003", "OR-PB04-004"], 31995018692, 95285014841, "d06577ffac8d2049f5a7", "6ca2a0022affad147479544c66fa6e1ef47d81988f2d236293a4676f4d669997"),
}
EXPECTED_SELECTION = (462, "9e1bf7d3835293f6b53ae88814241e95a977b972", "8943acd3ff04b8720f7a3a2071f628f370ac6db0", 31993627583, 95281347377, "PASS")
EXPECTED_WAVES = [("OR-PB04-A", 463, 2), ("OR-PB04-B", 464, 2), ("OR-PB04-C", 465, 1)]


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canon(value)).hexdigest()


def emit(log, chains, task, kind, previous_state, next_state, surface):
    seq = chains.get(task, {}).get("seq", 0) + 1
    previous_hash = chains.get(task, {}).get("hash", ZERO)
    event = {
        "event_id": f"{task}:{seq:02d}", "idempotency_key": f"ORCH-PROD-002:{task}:{seq:02d}",
        "task_id": task, "seq": seq, "event_type": kind,
        "previous_state": previous_state, "next_state": next_state,
        "context": {"conversation_id": "issue-461", "actor": "ORCH-PROD",
                    "gate_id": "ORCH-PROD-002", "write_surface": [surface]},
        "previous_event_hash": previous_hash,
    }
    event["event_hash"] = digest(event)
    chains[task] = {"seq": seq, "hash": event["event_hash"]}
    log.append(event)


def reconcile(data):
    if data["capacity"] != 2 or data["automatic_retries"] or data["public_release"]:
        raise ValueError("unsafe controls")
    selection = data["selection"]
    if tuple(selection[key] for key in ("pr", "head_sha", "merge_sha", "workflow_run_id", "job_id", "status")) != EXPECTED_SELECTION:
        raise ValueError("selection evidence mismatch")
    waves = data["waves"]
    if len(waves) != 3:
        raise ValueError("wave count")
    completed, log, chains = set(), [], {}
    states, locks, handoffs = {}, set(), 0
    max_locks, previous_merge = 0, selection["merge_sha"]
    results = []

    for wave, expected in zip(waves, EXPECTED_WAVES):
        if (wave["wave"], wave["pr"], len(wave["tasks"])) != expected:
            raise ValueError("wave shape/order mismatch")
        if wave["base_sha"] != previous_merge:
            raise ValueError("wave merge ancestry break")
        if len(wave["tasks"]) > data["capacity"]:
            raise ValueError("wave exceeds capacity")
        tasks = sorted(wave["tasks"], key=lambda item: item["sequence"])
        for task in tasks:
            tid = task["target_id"]
            expected_task = EXPECTED_TASKS.get(tid)
            observed = (task["county"], task["geoid"], task["dependencies"], wave["workflow_run_id"],
                        task["job_id"], task["production_run_id"], task["artifact_sha256"])
            if observed != expected_task:
                raise ValueError("task authority/evidence mismatch")
            if not set(task["dependencies"]).issubset(completed):
                raise ValueError("undeclared or unsatisfied dependency activation")
            if task["status"] != "PASS" or not all(task[key] for key in ("production_acceptance", "deterministic", "nesting_parity", "enrichment_guard")):
                raise ValueError("non-PASS production task")
            states[tid] = "BLOCKED"
            emit(log, chains, tid, "READY", "BLOCKED", "READY", "authority:read-only")
            states[tid] = "READY"
            emit(log, chains, tid, "DISPATCH", "READY", "DISPATCHED", "production:bounded")
            states[tid] = "DISPATCHED"
            emit(log, chains, tid, "LOCK_ACQUIRED", "DISPATCHED", "ACTIVE", tid)
            states[tid] = "ACTIVE"
            locks.add(tid)
            max_locks = max(max_locks, len(locks))
            if len(locks) > data["capacity"]:
                raise ValueError("capacity exceeded")

        for task in tasks:
            tid = task["target_id"]
            for surface in ("source-input", "nat-fac-generation", "qa-parity-evidence"):
                emit(log, chains, tid, "STAGE_START", "ACTIVE", "ACTIVE", surface)
                emit(log, chains, tid, "STAGE_COMPLETE", "ACTIVE", "ACTIVE", surface)
            emit(log, chains, tid, "PROMOTION_READY", "ACTIVE", "READY_FOR_HANDOFF", "promotion:internal")
            emit(log, chains, tid, "HANDOFF", "READY_FOR_HANDOFF", "COMPLETED", "handoff:internal")
            handoffs += 1
            emit(log, chains, tid, "LOCK_RELEASED", "COMPLETED", "COMPLETED", tid)
            locks.remove(tid)
            states[tid] = "COMPLETED"
            completed.add(tid)
            results.append({"target_id": tid, "status": "PASS", "wave": wave["wave"],
                            "workflow_run_id": wave["workflow_run_id"], "job_id": task["job_id"],
                            "production_run_id": task["production_run_id"],
                            "artifact_sha256": task["artifact_sha256"], "handoffs": 1, "held_locks": 0})
        previous_merge = wave["merge_sha"]

    previous = {}
    for event in log:
        tid = event["task_id"]
        if event["previous_event_hash"] != previous.get(tid, ZERO):
            raise ValueError("event chain break")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        if event["event_hash"] != digest(body):
            raise ValueError("event tamper")
        previous[tid] = event["event_hash"]
    if len(completed) != 5 or locks or handoffs != 5 or max_locks != 2:
        raise ValueError("invalid batch terminal state")
    return results, log, max_locks


def rejected(fn):
    try:
        fn()
    except (ValueError, AssertionError):
        return "REJECTED"
    raise AssertionError("negative probe accepted")


def mutate(data, wave, task, field, value):
    result = copy.deepcopy(data)
    result["waves"][wave]["tasks"][task][field] = value
    return result


def main():
    data = json.loads(FIXTURE.read_text())
    Draft202012Validator(json.loads(FIXTURE_SCHEMA.read_text())).validate(data)
    results, log, max_locks = reconcile(data)
    again = reconcile(copy.deepcopy(data))
    if canon((results, log, max_locks)) != canon(again):
        raise AssertionError("DAG replay not deterministic")
    probes = {
        "clatsop_blocks_coos": rejected(lambda: reconcile(mutate(data, 0, 0, "status", "REVIEW"))),
        "columbia_blocks_crook": rejected(lambda: reconcile(mutate(data, 0, 1, "status", "FAIL"))),
        "coos_blocks_curry": rejected(lambda: reconcile(mutate(data, 1, 0, "status", "FAIL"))),
        "crook_blocks_curry": rejected(lambda: reconcile(mutate(data, 1, 1, "status", "REVIEW"))),
        "undeclared_activation": rejected(lambda: reconcile(mutate(data, 1, 0, "dependencies", []))),
        "wave_ancestry": rejected(lambda: reconcile({**copy.deepcopy(data), "waves": [data["waves"][0], {**data["waves"][1], "base_sha": "0" * 40}, data["waves"][2]]})),
        "artifact_identity": rejected(lambda: reconcile(mutate(data, 2, 0, "artifact_sha256", "0" * 64))),
        "determinism": rejected(lambda: reconcile(mutate(data, 1, 0, "deterministic", False))),
        "parity": rejected(lambda: reconcile(mutate(data, 0, 0, "nesting_parity", False))),
        "enrichment": rejected(lambda: reconcile(mutate(data, 0, 1, "enrichment_guard", False))),
        "capacity": rejected(lambda: reconcile({**copy.deepcopy(data), "capacity": 3})),
        "automatic_retry": rejected(lambda: reconcile({**copy.deepcopy(data), "automatic_retries": True})),
        "public_release": rejected(lambda: reconcile({**copy.deepcopy(data), "public_release": True})),
        "selection": rejected(lambda: reconcile({**copy.deepcopy(data), "selection": {**data["selection"], "status": "FAIL"}})),
    }
    core = {"gate_id": "ORCH-PROD-002", "status": "PASS", "selection_verified": True,
            "capacity": 2, "wave_shape": [2, 2, 1], "tasks": results,
            "dependency_unlocks_verified": True, "fail_closed_verified": True,
            "max_held_locks": max_locks, "held_locks": 0, "handoffs": 5,
            "event_trace_sha256": digest(log), "deterministic": True, "tamper_probes": probes}
    report = {**core, "report_sha256": digest(core)}
    Draft202012Validator(json.loads(REPORT_SCHEMA.read_text())).validate(report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
