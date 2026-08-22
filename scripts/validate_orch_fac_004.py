#!/usr/bin/env python3
import copy, hashlib, importlib.util, json
from pathlib import Path
from jsonschema import Draft202012Validator

FIXTURE=Path("tests/fixtures/orch_fac_004_recovery.json")
INPUT_SCHEMA=Path("schemas/orch-fac-004-recovery.schema.json")
REPORT_SCHEMA=Path("schemas/orch-fac-004-report.schema.json")
ORCH2=Path("scripts/validate_orch_fac_002.py")
STAGES=("source","domain","qa","rel")

def load_orch2():
 spec=importlib.util.spec_from_file_location("orch2",ORCH2); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"))
def digest(v): return hashlib.sha256(canonical(v).encode()).hexdigest()
def validate(path,v):
 errors=list(Draft202012Validator(json.loads(path.read_text())).iter_errors(v)); assert not errors,"\n".join(e.message for e in errors)
def validate_history(case,state):
 assert (state["lock_state"]=="HELD")== (state["lock_owner"]!="NONE"), f"{case['case_id']}: lock owner mismatch"
 assert state["completed_stages"]==[s for s in STAGES if s in state["completed_stages"]], f"{case['case_id']}: stage order"
 seen={}
 for w in state["writes"]:
  assert w["key"]==f"{case['idempotency_key']}:{w['stage']}", f"{case['case_id']}: write identity mismatch"
  assert w["stage"] in state["completed_stages"], f"{case['case_id']}: write without completed stage"
  assert w["key"] not in seen, f"{case['case_id']}: duplicate committed key"
  seen[w["key"]]=w["sha256"]
 assert len(seen)==len(state["completed_stages"]), f"{case['case_id']}: completed stage/write mismatch"
 return seen
def replay_terminal(case,state,event_name="NOOP_TERMINAL_REPLAY"):
 assert state["lock_state"]!="HELD" and state["lock_owner"]=="NONE"
 status=state["terminal_status"]; assert status in {"PASS","REVIEW","FAIL"}
 return state,[{"event":event_name,"task_id":case["task_id"],"idempotency_key":case["idempotency_key"],"terminal_status":status}]
def recover(case,orch2):
 state=copy.deepcopy(case["initial"]); writes=validate_history(case,state); rec=case["recovery"]; events=[]; suppressed=0
 assert rec["idempotency_key"]==case["idempotency_key"], f"{case['case_id']}: retry changed identity"
 if state["terminal_status"] is not None:
  before=canonical(state); state,events=replay_terminal(case,state); assert canonical(state)==before
  return finish(case,state,events,suppressed)
 if state["lock_state"]=="HELD":
  required="RECOVER_STALE" if rec["reason"]=="stale_lock" else "RECOVER_INTERRUPTED"
  assert rec["action"]==required, f"{case['case_id']}: explicit recovery action required"
  events.append({"event":"LOCK_RELEASED","owner":state["lock_owner"],"reason":rec["reason"]})
  state["lock_state"]="RELEASED"; state["lock_owner"]="NONE"
 else:
  assert rec["action"]=="RETRY", f"{case['case_id']}: explicit retry required"
 state["retry_count"]+=1
 events.append({"event":"RETRY_REQUESTED","task_id":case["task_id"],"idempotency_key":rec["idempotency_key"],"retry_count":state["retry_count"],"reason":rec["reason"]})
 state["lock_state"]="HELD"; state["lock_owner"]=rec["new_owner"]; events.append({"event":"LOCK_ACQUIRED","owner":rec["new_owner"],"retry_count":state["retry_count"]})
 terminal=None
 for attempt in rec["attempts"]:
  expected=f"{case['idempotency_key']}:{attempt['stage']}"; assert attempt["key"]==expected
  if attempt["key"] in writes:
   assert writes[attempt["key"]]==attempt["sha256"], f"{case['case_id']}: conflicting duplicate write"
   suppressed+=1; events.append({"event":"WRITE_SUPPRESSED","stage":attempt["stage"],"key":attempt["key"],"sha256":attempt["sha256"]}); continue
  assert attempt["stage"] not in state["completed_stages"], f"{case['case_id']}: completed stage reapplied"
  next_stage=STAGES[len(state["completed_stages"])]; assert attempt["stage"]==next_stage, f"{case['case_id']}: stage order violation"
  status=orch2.load_orch1().qa_status(attempt["checks"])
  writes[attempt["key"]]=attempt["sha256"]; state["writes"].append({"stage":attempt["stage"],"key":attempt["key"],"sha256":attempt["sha256"]}); state["completed_stages"].append(attempt["stage"])
  events.append({"event":"WRITE_APPLIED","stage":attempt["stage"],"key":attempt["key"],"sha256":attempt["sha256"],"status":status})
  if status!="PASS": terminal=status; break
 if terminal is None:
  terminal="PASS" if state["completed_stages"]==list(STAGES) else None
 assert terminal is not None, f"{case['case_id']}: retry did not reach terminal"
 state["terminal_status"]=terminal; state["lock_state"]="RELEASED"; state["lock_owner"]="NONE"; events.append({"event":"LOCK_RELEASED","owner":rec["new_owner"],"reason":"terminal"})
 if terminal=="PASS": events.append({"event":"HANDOFF","target":"PROGRAM-CONTROL"})
 elif terminal=="REVIEW": events.append({"event":"EXCEPTION","target":"EXCEPTION-QUEUE"})
 else: events.append({"event":"REMEDIATION","target":"REMEDIATION"})
 validate_history(case,state)
 # A repeated delivery of recovered terminal state is a byte-stable no-op.
 before=canonical(state); replayed,replay_events=replay_terminal(case,copy.deepcopy(state)); assert canonical(replayed)==before
 events.extend(replay_events)
 return finish(case,state,events,suppressed)
def finish(case,state,events,suppressed):
 terminal_events=[e for e in events if e["event"] in {"HANDOFF","EXCEPTION","REMEDIATION"}]
 if events[0]["event"]=="NOOP_TERMINAL_REPLAY":
  handoffs=1 if state["terminal_status"]=="PASS" else 0; exceptions=1 if state["terminal_status"]!="PASS" else 0
 else:
  assert len(terminal_events)==1
  handoffs=sum(e["event"]=="HANDOFF" for e in terminal_events); exceptions=sum(e["event"] in {"EXCEPTION","REMEDIATION"} for e in terminal_events)
 return {"case_id":case["case_id"],"task_id":case["task_id"],"terminal_status":state["terminal_status"],"retry_count":state["retry_count"],"writes":len(state["writes"]),"handoffs":handoffs,"exceptions":exceptions,"held_locks":int(state["lock_state"]=="HELD"),"duplicate_writes_suppressed":suppressed,"events":events,"state_sha256":digest(state)}
def conflict_probe(data,orch2):
 case=copy.deepcopy(next(c for c in data["cases"] if c["case_id"]=="interrupted-resume-pass"))
 case["recovery"]["attempts"][0]["sha256"]="ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
 try: recover(case,orch2)
 except AssertionError as e: assert "conflicting duplicate write" in str(e); return
 raise AssertionError("conflicting duplicate was not rejected")
def main():
 data=json.loads(FIXTURE.read_text()); validate(INPUT_SCHEMA,data); assert len({c["case_id"] for c in data["cases"]})==len(data["cases"])
 orch2=load_orch2(); first=sorted((recover(c,orch2) for c in data["cases"]),key=lambda r:r["case_id"]); second=sorted((recover(c,orch2) for c in reversed(data["cases"])),key=lambda r:r["case_id"])
 assert first==second; conflict_probe(data,orch2)
 by={r["case_id"]:r for r in first}; assert by["interrupted-resume-pass"]["duplicate_writes_suppressed"]==1
 assert by["terminal-retry-noop"]["retry_count"]==1 and by["terminal-retry-noop"]["events"][0]["event"]=="NOOP_TERMINAL_REPLAY"
 assert by["stale-lock-reclaim"]["events"][0]["event"]=="LOCK_RELEASED"
 assert by["recovery-review"]["terminal_status"]=="REVIEW" and by["recovery-fail"]["terminal_status"]=="FAIL"
 assert all(r["held_locks"]==0 for r in first)
 output={"schema_version":1,"gate_id":"ORCH-FAC-004","status":"PASS","deterministic":True,"idempotent_replay":True,"fixture_sha256":hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),"results":first,"report_sha256":digest(first)}
 validate(REPORT_SCHEMA,output); print(json.dumps(output,indent=2,sort_keys=True))
if __name__=="__main__": main()
