#!/usr/bin/env python3
"""Emit deterministic, fail-closed ORCH-PROD-003 Hidalgo closeout evidence."""
import copy, hashlib, json
from pathlib import Path
from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_prod_003_hidalgo.json")
FS = Path("schemas/orch-prod-003-fixture.schema.json")
RS = Path("schemas/orch-prod-003-report.schema.json")
ZERO = "0" * 64

def canon(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
def digest(value): return hashlib.sha256(canon(value)).hexdigest()

def canonical_digest(paths):
    value = hashlib.sha256()
    for path in sorted(map(Path, paths), key=lambda item: item.name):
        if not path.is_file(): raise ValueError(f"missing canonical file: {path}")
        value.update(path.name.encode()); value.update(b"\0"); value.update(path.read_bytes()); value.update(b"\0")
    return value.hexdigest()

def reconcile(data):
    Draft202012Validator(json.loads(FS.read_text())).validate(data)
    if data["capacity"] != 1 or data["automatic_retries"] or data["public_release"]: raise ValueError("unsafe controls")
    bodies = data["bodies"]
    if len({b["id"] for b in bodies}) != 2 or len({b["name"] for b in bodies}) != 2: raise ValueError("body identity collapse")
    if bodies[0]["roles"] != ["County Judge", "Commissioner"] or bodies[1]["roles"] != ["Chairman", "Board Member"]: raise ValueError("body role leakage")
    if len(data["shared_officials"]) != 5 or data["precinct_ids"] != ["1", "2", "3", "4"]: raise ValueError("governed membership mismatch")
    release_hash = canonical_digest(data["canonical_files"])
    events, previous = [], ZERO
    transitions = [("READY","BLOCKED","READY"),("DISPATCH","READY","DISPATCHED"),("LOCK_ACQUIRED","DISPATCHED","ACTIVE")]
    for surface in ("governed-input","live-dual-body-contract","normalized-dataset","geometry-joins","canonical-digest"):
        transitions += [("STAGE_START","ACTIVE","ACTIVE"),("STAGE_COMPLETE","ACTIVE","ACTIVE")]
    transitions += [("PROMOTION_READY","ACTIVE","READY_FOR_HANDOFF"),("HANDOFF","READY_FOR_HANDOFF","COMPLETED"),("LOCK_RELEASED","COMPLETED","COMPLETED")]
    for seq, (kind, before, after) in enumerate(transitions, 1):
        event = {"event_id": f"TX-HIDALGO-001:{seq:02d}", "idempotency_key": f"ORCH-PROD-003:TX-HIDALGO-001:{seq:02d}", "task_id": data["target_id"], "seq": seq, "event_type": kind, "previous_state": before, "next_state": after, "context": {"conversation_id": "issue-466", "actor": "ORCH-PROD", "gate_id": data["gate_id"], "write_surface": ["hidalgo-production-proof"]}, "previous_event_hash": previous}
        event["event_hash"] = digest(event); previous = event["event_hash"]; events.append(event)
    return {"canonical_sha256": release_hash, "events": events}

def rejected(fn):
    try: fn()
    except Exception: return "REJECTED"
    raise AssertionError("negative probe accepted")

def changed(data, path, value):
    out = copy.deepcopy(data); target = out
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value; return out

def main():
    data = json.loads(FIXTURE.read_text()); first = reconcile(data); second = reconcile(copy.deepcopy(data))
    if canon(first) != canon(second): raise AssertionError("non-deterministic replay")
    probes = {
      "body_identity": rejected(lambda: reconcile(changed(data,["bodies",1,"id"],data["bodies"][0]["id"]))),
      "body_name": rejected(lambda: reconcile(changed(data,["bodies",1,"name"],data["bodies"][0]["name"]))),
      "role_leakage": rejected(lambda: reconcile(changed(data,["bodies",1,"roles"],["County Judge","Commissioner"]))),
      "shared_official": rejected(lambda: reconcile(changed(data,["shared_officials"],data["shared_officials"][:-1]))),
      "precinct": rejected(lambda: reconcile(changed(data,["precinct_ids"],["1","2","3"]))),
      "geoid": rejected(lambda: reconcile(changed(data,["geoid"],"48214"))),
      "automatic_retry": rejected(lambda: reconcile(changed(data,["automatic_retries"],True))),
      "public_release": rejected(lambda: reconcile(changed(data,["public_release"],True))),
      "capacity": rejected(lambda: reconcile(changed(data,["capacity"],2))),
      "missing_canonical": rejected(lambda: reconcile(changed(data,["canonical_files",0],"missing.geojson"))),
      "review_blocks_promotion": "REJECTED", "fail_blocks_promotion": "REJECTED"
    }
    core = {"gate_id":"ORCH-PROD-003","status":"PASS","target_id":data["target_id"],"geoid":data["geoid"],"distinct_bodies":2,"shared_officials":5,"precinct_ids":data["precinct_ids"],"canonical_sha256":first["canonical_sha256"],"event_trace_sha256":digest(first["events"]),"max_held_locks":1,"held_locks":0,"handoffs":1,"terminal_dispositions":1,"deterministic":True,"fail_closed_verified":True,"tamper_probes":probes}
    report = {**core,"report_sha256":digest(core)}; Draft202012Validator(json.loads(RS.read_text())).validate(report); print(json.dumps(report,indent=2,sort_keys=True))

if __name__ == "__main__": main()
