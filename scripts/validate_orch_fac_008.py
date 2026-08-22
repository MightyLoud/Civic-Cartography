#!/usr/bin/env python3
"""ORCH-FAC-008 read-only replay of the frozen MB100-100 completion row."""
import copy
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_fac_008_multnomah.json")
REGISTER = Path("evidence/measured-batch-100/completion-register.csv")
FIXTURE_SCHEMA = Path("schemas/orch-fac-008-fixture.schema.json")
REPORT_SCHEMA = Path("schemas/orch-fac-008-report.schema.json")
GATES = [
    ("RAW", "raw_exists"), ("NORMALIZED", "normalized_exists"),
    ("IDENTIFIER_JOIN", "identifier_join_ok"), ("QA", "qa_ok"),
    ("PARITY", "parity_ok"), ("PROVENANCE", "source_provenance_ok"),
    ("COMPLETION", "complete_ok"),
]
EXACT = {
    "target_id": "target_id", "jurisdiction_name": "jurisdiction_name",
    "state": "state", "evaluation_id": "evaluation_id",
    "source_manifest_sha256": "source_manifest_sha256",
    "manifest_sha256": "manifest_sha256",
    "run_id": "first_run_id",
}
ZERO_HASH = "0" * 64


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_register(data, target_id):
    rows = list(csv.DictReader(io.StringIO(data.decode())))
    matches = [row for row in rows if row["target_id"] == target_id]
    if len(matches) != 1:
        raise ValueError(f"expected one {target_id} row, found {len(matches)}")
    return matches[0]


def validate_authority(authority, row, register_bytes):
    if git_blob_sha(register_bytes) != authority["completion_register_blob"]:
        raise ValueError("completion-register blob mismatch")
    for authority_field, row_field in EXACT.items():
        if str(authority[authority_field]) != row[row_field]:
            raise ValueError(f"{authority_field} identity mismatch")
    if row["first_run_id"] != row["second_run_id"] or row["first_run_id"] != authority["run_id"]:
        raise ValueError("deterministic run identity mismatch")
    match = re.fullmatch(r"https://github\.com/MightyLoud/Civic-Cartography/actions/runs/(\d+)", row["evidence_ref"])
    if not match or int(match.group(1)) != authority["evidence_run_id"]:
        raise ValueError("evidence-run identity mismatch")
    facts = []
    for gate, field in GATES:
        if row[field].upper() != "TRUE":
            raise ValueError(f"required gate false: {field}")
        facts.append({"gate": gate, "status": "PASS"})
    return facts


def event(seq, event_type, previous_state, next_state, actor, gate, surface):
    return {
        "event_id": f"MB100-100-{seq:03d}",
        "idempotency_key": f"ORCH-FAC-008:MB100-100:{seq:03d}",
        "task_id": "MB100-100",
        "seq": seq,
        "event_type": event_type,
        "previous_state": previous_state,
        "next_state": next_state,
        "context": {
            "conversation_id": "ORCH-FAC-008-MB100-100",
            "actor": actor,
            "gate_id": gate,
            "write_surface": [surface],
        },
    }


def build_trace(facts):
    events = [
        event(1, "READY", "BLOCKED", "READY", "ORCH", "ORCH-FAC-008", "completion-register:read-only"),
        event(2, "DISPATCH", "READY", "DISPATCHED", "ORCH", "ORCH-FAC-008", "completion-register:read-only"),
        event(3, "LOCK_ACQUIRED", "DISPATCHED", "ACTIVE", "REPLAY-WORKER", "ORCH-FAC-008", "ephemeral:replay"),
    ]
    seq = 4
    for fact in facts:
        gate = fact["gate"]
        events.append(event(seq, "STAGE_START", "ACTIVE", "ACTIVE", "REPLAY-WORKER", gate, "completion-register:read-only"))
        seq += 1
        events.append(event(seq, "STAGE_COMPLETE", "ACTIVE", "ACTIVE", "REPLAY-WORKER", gate, "ephemeral:qa-facts"))
        seq += 1
    events.extend([
        event(seq, "PROMOTION_READY", "ACTIVE", "READY_FOR_HANDOFF", "REL-FAC", "REL-FAC-001", "ephemeral:promotion"),
        event(seq + 1, "LOCK_RELEASED", "READY_FOR_HANDOFF", "READY_FOR_HANDOFF", "REPLAY-WORKER", "ORCH-FAC-008", "ephemeral:replay"),
        event(seq + 2, "HANDOFF", "READY_FOR_HANDOFF", "COMPLETED", "ORCH", "ORCH-FAC-008", "ephemeral:closeout"),
    ])
    previous = ZERO_HASH
    chained = []
    for raw in events:
        record = {**raw, "previous_event_hash": previous}
        record["event_hash"] = sha256(record)
        previous = record["event_hash"]
        chained.append(record)
    return chained


def replay(authority, row, register_bytes):
    facts = validate_authority(authority, row, register_bytes)
    trace = build_trace(facts)
    state, lock, promotion, handoffs, previous = "BLOCKED", "RELEASED", False, 0, ZERO_HASH
    for expected_seq, record in enumerate(trace, 1):
        if record["seq"] != expected_seq or record["previous_event_hash"] != previous:
            raise ValueError("non-append-only event sequence")
        body = {key: value for key, value in record.items() if key != "event_hash"}
        if record["event_hash"] != sha256(body):
            raise ValueError("event hash mismatch")
        if record["previous_state"] != state:
            raise ValueError("event state mismatch")
        kind = record["event_type"]
        if kind == "LOCK_ACQUIRED":
            if lock != "RELEASED":
                raise ValueError("lock already held")
            lock = "HELD"
        elif kind in {"STAGE_START", "STAGE_COMPLETE"} and lock != "HELD":
            raise ValueError("mutating replay event without lock")
        elif kind == "PROMOTION_READY":
            promotion = all(fact["status"] == "PASS" for fact in facts)
            if not promotion:
                raise ValueError("promotion without all gates")
        elif kind == "LOCK_RELEASED":
            if lock != "HELD":
                raise ValueError("lock not held")
            lock = "RELEASED"
        elif kind == "HANDOFF":
            if lock != "RELEASED" or not promotion:
                raise ValueError("handoff before promotion/release")
            handoffs += 1
        state = record["next_state"]
        previous = record["event_hash"]
    if state != "COMPLETED" or lock != "RELEASED" or not promotion or handoffs != 1:
        raise ValueError("derived closeout state invalid")
    return facts, trace, {"promotion_ready": promotion, "held_locks": 0, "handoffs": handoffs}


def reject(fn):
    try:
        fn()
    except (ValueError, AssertionError):
        return "REJECTED"
    raise AssertionError("tamper probe was accepted")


def main():
    fixture = json.loads(FIXTURE.read_text())
    Draft202012Validator(json.loads(FIXTURE_SCHEMA.read_text())).validate(fixture)
    authority = fixture["authority"]
    register_bytes = REGISTER.read_bytes()
    row = load_register(register_bytes, authority["target_id"])
    facts, trace, derived = replay(authority, row, register_bytes)

    facts2, trace2, derived2 = replay(copy.deepcopy(authority), copy.deepcopy(row), bytes(register_bytes))
    if canonical_bytes((facts, trace, derived)) != canonical_bytes((facts2, trace2, derived2)):
        raise AssertionError("second replay is not byte deterministic")

    probes = {}
    mutations = {
        "target_identity": ("target_id", "MB100-999"),
        "evaluation_identity": ("evaluation_id", "0" * 20),
        "source_hash": ("source_manifest_sha256", "0" * 64),
        "manifest_hash": ("manifest_sha256", "0" * 64),
        "run_identity": ("first_run_id", "tampered-run"),
        "second_run_identity": ("second_run_id", "tampered-run"),
        "gate_false": ("qa_ok", "FALSE"),
        "evidence_run_identity": ("evidence_ref", "https://github.com/MightyLoud/Civic-Cartography/actions/runs/1"),
    }
    for name, (field, value) in mutations.items():
        changed = dict(row)
        changed[field] = value
        probes[name] = reject(lambda changed=changed: replay(authority, changed, register_bytes))
    probes["register_blob"] = reject(lambda: replay(authority, row, register_bytes + b"\n"))

    core = {
        "gate_id": "ORCH-FAC-008", "status": "PASS",
        "mode": "READ_ONLY_EVIDENCE_REPLAY", "target_id": authority["target_id"],
        "register_blob_verified": True, "evidence_run_id": authority["evidence_run_id"],
        "qa_facts": facts, **derived, "event_count": len(trace),
        "event_trace_sha256": sha256(trace), "deterministic": True,
        "tamper_probes": probes,
    }
    report = {**core, "report_sha256": sha256(core)}
    Draft202012Validator(json.loads(REPORT_SCHEMA.read_text())).validate(report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
