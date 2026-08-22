#!/usr/bin/env python3
import copy,hashlib,importlib.util,json
from pathlib import Path
from jsonschema import Draft202012Validator
FIXTURE=Path("tests/fixtures/orch_fac_006_scheduler.json");INPUT_SCHEMA=Path("schemas/orch-fac-006-scheduler.schema.json");REPORT_SCHEMA=Path("schemas/orch-fac-006-report.schema.json");ORCH2=Path("scripts/validate_orch_fac_002.py")
def load_orch2():
 s=importlib.util.spec_from_file_location("orch2",ORCH2);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"))
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def validate(p,v):
 e=list(Draft202012Validator(json.loads(p.read_text())).iter_errors(v));assert not e,"\n".join(x.message for x in e)
def is_ready(t):
 if t["state_source"]!="ORCH-FAC-005:READY":return False
 return all(p["status"]=="PASS" for p in t["predecessors"])
def run_case(case,aging,orch2):
 original=canonical(case["tasks"]);tasks={t["task_id"]:t for t in case["tasks"]};assert len(tasks)==len(case["tasks"])
 pending={tid for tid,t in tasks.items() if is_ready(t)};nonready=sorted(set(tasks)-pending);wait={tid:tasks[tid]["initial_wait"] for tid in pending}
 events=[];rounds=[];exclusions=[];held=set();maxheld=0;round_no=0
 for tid in nonready:
  reason=tasks[tid]["state_source"];exclusions.append({"task_id":tid,"round":0,"reason":reason});events.append({"event":"UNSCHEDULED","task_id":tid,"reason":reason})
 while pending:
  round_no+=1;ranked=sorted(pending,key=lambda tid:(-(tasks[tid]["priority"]+wait[tid]*aging),tid))
  chosen=[];surfaces=set()
  for tid in ranked:
   reason=None;s=set(tasks[tid]["write_surface"])
   if len(chosen)>=case["capacity"]:reason="CAPACITY"
   elif surfaces&s:reason="OVERLAP"
   if reason:
    exclusions.append({"task_id":tid,"round":round_no,"reason":reason});events.append({"event":"UNSCHEDULED","task_id":tid,"round":round_no,"reason":reason,"effective_priority":tasks[tid]["priority"]+wait[tid]*aging})
   else:chosen.append(tid);surfaces|=s
  assert chosen;rounds.append(chosen)
  for tid in chosen:
   events.append({"event":"DISPATCH","task_id":tid,"round":round_no,"effective_priority":tasks[tid]["priority"]+wait[tid]*aging});held.add(tid);events.append({"event":"LOCK_ACQUIRED","task_id":tid,"round":round_no});maxheld=max(maxheld,len(held));assert len(held)<=case["capacity"]
  for tid in chosen:
   status=orch2.load_orch1().qa_status(tasks[tid]["terminal_checks"]);events.append({"event":"TERMINAL","task_id":tid,"status":status});held.remove(tid);events.append({"event":"LOCK_RELEASED","task_id":tid,"round":round_no});assert status=="PASS"
   pending.remove(tid)
  for tid in pending:wait[tid]+=1
 assert not held and canonical(case["tasks"])==original
 return {"case_id":case["case_id"],"capacity":case["capacity"],"rounds":rounds,"max_held_locks":maxheld,"held_locks":0,"exclusions":exclusions,"events":events,"task_data_unchanged":True}
def main():
 data=json.loads(FIXTURE.read_text());validate(INPUT_SCHEMA,data);orch2=load_orch2()
 first=sorted((run_case(c,data["aging_step"],orch2) for c in data["cases"]),key=lambda r:r["case_id"])
 perm=sorted((run_case({**c,"tasks":list(reversed(c["tasks"]))},data["aging_step"],orch2) for c in reversed(data["cases"])),key=lambda r:r["case_id"]);assert first==perm
 by={r["case_id"]:r for r in first}
 assert by["capacity-priority"]["rounds"][0]==["A","B"] and by["capacity-priority"]["max_held_locks"]==2
 assert by["deterministic-tie"]["rounds"][0]==["A","B"]
 assert by["aging-prevents-starvation"]["rounds"][1]==["OLD"]
 assert by["overlap-exclusion"]["rounds"][0]==["A","C"] and any(e["reason"]=="OVERLAP" and e["task_id"]=="B" for e in by["overlap-exclusion"]["exclusions"])
 assert {e["reason"] for e in by["nonready-exclusion"]["exclusions"]}>={"READ_ONLY","HOLD","BLOCKED"} and by["nonready-exclusion"]["rounds"]==[["READY"]]
 assert by["dependency-derived-ready"]["rounds"]==[["GOOD"]]
 output={"schema_version":1,"gate_id":"ORCH-FAC-006","status":"PASS","deterministic":True,"permutation_stable":True,"fixture_sha256":hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),"results":first,"report_sha256":digest(first)};validate(REPORT_SCHEMA,output);print(json.dumps(output,indent=2,sort_keys=True))
if __name__=="__main__":main()
