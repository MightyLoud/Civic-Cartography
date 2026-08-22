#!/usr/bin/env python3
import hashlib, importlib.util, json
from pathlib import Path
from jsonschema import Draft202012Validator
FIXTURE=Path("tests/fixtures/orch_fac_005_dag.json"); INPUT_SCHEMA=Path("schemas/orch-fac-005-dag.schema.json"); REPORT_SCHEMA=Path("schemas/orch-fac-005-report.schema.json"); ORCH2=Path("scripts/validate_orch_fac_002.py")
def load_orch2():
 s=importlib.util.spec_from_file_location("orch2",ORCH2);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"))
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def validate(path,v):
 e=list(Draft202012Validator(json.loads(path.read_text())).iter_errors(v));assert not e,"\n".join(x.message for x in e)
def graph(tasks):
 ids=[t["task_id"] for t in tasks];assert len(ids)==len(set(ids)),"duplicate task_id"
 by={t["task_id"]:t for t in tasks}
 for t in tasks:
  for d in t["depends_on"]:assert d in by,f"unknown dependency {d}"
 visiting=set();done=set()
 def visit(n):
  if n in visiting:raise AssertionError("cycle detected")
  if n in done:return
  visiting.add(n)
  for d in by[n]["depends_on"]:visit(d)
  visiting.remove(n);done.add(n)
 for n in sorted(by):visit(n)
 return by
def run_case(case,orch2):
 try: tasks=graph(case["tasks"])
 except AssertionError as e:
  if "cycle detected" not in str(e):raise
  return {"case_id":case["case_id"],"cycle_rejected":True,"ready_order":[],"blocked":sorted(t["task_id"] for t in case["tasks"]),"exception_routes":0,"remediation_routes":0,"held_locks":0,"events":[{"event":"DAG_REJECTED","reason":"CYCLE"}]}
 states={tid:"BLOCKED" for tid in tasks};terminal={};events=[];ready_emitted=set();ready_order=[];held=set()
 while True:
  ready=sorted(tid for tid,t in tasks.items() if states[tid]=="BLOCKED" and all(terminal.get(d)=="PASS" for d in t["depends_on"]))
  if not ready:break
  for tid in ready:
   assert tid not in ready_emitted;ready_emitted.add(tid);states[tid]="READY";events.append({"event":"READY","task_id":tid,"held_locks":len(held)})
  assert not held,"readiness acquired lock";ready_order.append(ready)
  wave=[];surfaces=set()
  for tid in ready:
   surface=set(tasks[tid]["write_surface"])
   if not(surface&surfaces):wave.append(tid);surfaces|=surface
  # Any overlapping READY task remains READY and is dispatched in a later wave.
  while wave:
   for tid in wave:
    assert states[tid]=="READY";events.append({"event":"DISPATCH","task_id":tid});held.add(tid);events.append({"event":"LOCK_ACQUIRED","task_id":tid})
   for tid in wave:
    checks=tasks[tid]["terminal_checks"];assert checks,f"{tid}: dispatched task lacks terminal evidence"
    status=orch2.load_orch1().qa_status(checks);terminal[tid]=status;states[tid]=status;events.append({"event":"TERMINAL","task_id":tid,"status":status});held.remove(tid);events.append({"event":"LOCK_RELEASED","task_id":tid})
   remaining=sorted(t for t in ready if states[t]=="READY")
   wave=[];surfaces=set()
   for tid in remaining:
    surface=set(tasks[tid]["write_surface"])
    if not(surface&surfaces):wave.append(tid);surfaces|=surface
 blocked=sorted(tid for tid,s in states.items() if s=="BLOCKED")
 exception_routes=remediation_routes=0
 for tid in blocked:
  ancestors=[d for d in tasks[tid]["depends_on"] if terminal.get(d) in {"REVIEW","FAIL"}]
  if ancestors:
   status="FAIL" if any(terminal[d]=="FAIL" for d in ancestors) else "REVIEW";target="REMEDIATION" if status=="FAIL" else "EXCEPTION-QUEUE"
   events.append({"event":"BLOCKED_CONTEXT","task_id":tid,"predecessors":sorted(ancestors),"status":status,"target":target})
   remediation_routes+=status=="FAIL";exception_routes+=status=="REVIEW"
 assert not held
 assert sum(e["event"]=="READY" for e in events)==len(ready_emitted)
 for tid in ready_emitted:assert sum(e["event"]=="READY" and e["task_id"]==tid for e in events)==1
 for e in events:
  if e["event"]=="LOCK_ACQUIRED":
   i=events.index(e);assert any(x["event"]=="DISPATCH" and x["task_id"]==e["task_id"] for x in events[:i])
 return {"case_id":case["case_id"],"cycle_rejected":False,"ready_order":ready_order,"blocked":blocked,"exception_routes":exception_routes,"remediation_routes":remediation_routes,"held_locks":0,"events":events}
def main():
 data=json.loads(FIXTURE.read_text());validate(INPUT_SCHEMA,data);orch2=load_orch2()
 first=sorted((run_case(c,orch2) for c in data["cases"]),key=lambda r:r["case_id"])
 perm=sorted((run_case({**c,"tasks":list(reversed(c["tasks"]))},orch2) for c in reversed(data["cases"])),key=lambda r:r["case_id"])
 assert first==perm,"not permutation-stable"
 by={r["case_id"]:r for r in first}
 assert by["linear-chain"]["ready_order"]==[["SRC"],["DOMAIN"],["QA"],["REL"]]
 assert by["diamond"]["ready_order"]==[["ROOT"],["LEFT","RIGHT"],["JOIN"]]
 assert by["parallel-roots"]["ready_order"][0]==["A","B"]
 assert by["review-blocks-child"]["exception_routes"]==1
 assert by["fail-blocks-descendants"]["remediation_routes"]>=1
 assert by["cycle-rejected"]["cycle_rejected"]
 output={"schema_version":1,"gate_id":"ORCH-FAC-005","status":"PASS","deterministic":True,"permutation_stable":True,"fixture_sha256":hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),"results":first,"report_sha256":digest(first)}
 validate(REPORT_SCHEMA,output);print(json.dumps(output,indent=2,sort_keys=True))
if __name__=="__main__":main()
