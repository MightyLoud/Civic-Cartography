#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
from jsonschema import Draft202012Validator

FIXTURE=Path("tests/fixtures/orch_fac_003_batches.json")
FIXTURE_SCHEMA=Path("schemas/orch-fac-003-batch.schema.json")
REPORT_SCHEMA=Path("schemas/orch-fac-003-report.schema.json")
ORCH2=Path("scripts/validate_orch_fac_002.py")

def load_orch2():
    spec=importlib.util.spec_from_file_location("orch_fac_002",ORCH2)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def validate(path,value):
    errors=list(Draft202012Validator(json.loads(path.read_text())).iter_errors(value))
    assert not errors, "\n".join(e.message for e in errors)

def schedule(children,limit):
    pending=sorted(children,key=lambda c:c["task_id"])
    waves=[]; queued=[]
    while pending:
        wave=[]; surfaces=set()
        for child in list(pending):
            overlap=bool(surfaces & set(child["write_surface"]))
            if len(wave)<limit and not overlap:
                wave.append(child); surfaces.update(child["write_surface"]); pending.remove(child)
            else:
                queued.append({"event":"queued","task_id":child["task_id"],"wave":len(waves)+1,"reason":"CAPACITY" if len(wave)>=limit else "OVERLAP"})
        assert wave, "scheduler deadlock"
        waves.append(wave)
    return waves,queued

def normalize_child(child,result,wave,events):
    return {"task_id":child["task_id"],"terminal_status":result["terminal_status"],"promotion_status":result["promotion_status"],"release_status":result["release_status"],"held_locks":result["held_locks"],"wave":wave,"events":events+result["events"]}

def run_case(case,limit,nonwriting,orch2):
    waves,queued=schedule(case["children"],limit)
    results=[]; held=set()
    queued_by_task={}
    for event in queued: queued_by_task.setdefault(event["task_id"],[]).append(event)
    for wave_no,wave in enumerate(waves,1):
        wave_surfaces=set()
        for child in wave:
            assert not (wave_surfaces & set(child["write_surface"])), "overlap acquired in same wave"
            wave_surfaces.update(child["write_surface"])
            prefix=list(queued_by_task.get(child["task_id"],[]))
            if child["worker"] in nonwriting:
                assert child["task_id"] not in held
                rejected={"terminal_status":"REVIEW","promotion_status":"QUEUED","release_status":"HOLD","held_locks":0,"events":[{"event":"reject","actor":child["worker"],"reason":"READ_ONLY"},{"event":"route","status":"REVIEW","target":"EXCEPTION-QUEUE"}]}
                results.append(normalize_child(child,rejected,wave_no,prefix))
                continue
            assert child["task_id"] not in held
            held.add(child["task_id"]); prefix.append({"event":"batch_acquire","task_id":child["task_id"],"wave":wave_no,"write_surface":sorted(child["write_surface"])})
            orch_case={"case_id":child["task_id"],"domain_factory":child["domain_factory"],"final_handoff":"PROGRAM-CONTROL","stage_checks":child["stage_checks"]}
            child_result=orch2.run_case(orch_case,nonwriting,orch2.load_orch1())
            held.remove(child["task_id"]); prefix.append({"event":"batch_release","task_id":child["task_id"],"wave":wave_no})
            results.append(normalize_child(child,child_result,wave_no,prefix))
        assert not held, "wave ended with locks held"
    results=sorted(results,key=lambda r:r["task_id"])
    assert len(results)==len(case["children"]) and all(r["held_locks"]==0 for r in results)
    fail=sum(r["terminal_status"]=="FAIL" for r in results); review=sum(r["terminal_status"]=="REVIEW" for r in results)
    ready=sum(r["promotion_status"]=="READY" for r in results)
    status="FAIL" if fail else ("REVIEW" if review else "PASS")
    assert status!="PASS" or ready==len(results), "false batch PASS"
    return {"case_id":case["case_id"],"batch_status":status,"promotion_ready":ready,"review":review,"fail":fail,"waves":len(waves),"queued_events":len(queued),"held_locks":0,"all_terminal":True,"children":results}

def main():
    data=json.loads(FIXTURE.read_text()); validate(FIXTURE_SCHEMA,data)
    ids=[c["case_id"] for c in data["cases"]]; assert len(ids)==len(set(ids))
    orch2=load_orch2(); nonwriting=set(data["nonwriting_workers"])
    first=[run_case(c,data["max_parallel"],nonwriting,orch2) for c in data["cases"]]
    second=[run_case(c,data["max_parallel"],nonwriting,orch2) for c in data["cases"]]
    permuted=[run_case({**c,"children":list(reversed(c["children"]))},data["max_parallel"],nonwriting,orch2) for c in data["cases"]]
    assert first==second==permuted, "report is not deterministic and permutation-stable"
    by_id={r["case_id"]:r for r in first}
    assert by_id["parallel-clean-pass"]["waves"]==2 and by_id["parallel-clean-pass"]["batch_status"]=="PASS"
    assert by_id["overlap-queues"]["queued_events"]>0 and by_id["overlap-queues"]["waves"]==2
    assert by_id["mixed-review-fail-isolation"]["batch_status"]=="FAIL" and by_id["mixed-review-fail-isolation"]["promotion_ready"]==1 and by_id["mixed-review-fail-isolation"]["review"]==1
    ro=by_id["read-only-rejected"]; mon=next(c for c in ro["children"] if c["task_id"]=="MON-001")
    assert all(e["event"]!="batch_acquire" for e in mon["events"]) and mon["terminal_status"]=="REVIEW"
    output={"schema_version":1,"gate_id":"ORCH-FAC-003","status":"PASS","deterministic":True,"permutation_stable":True,"fixture_sha256":hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),"results":first,"report_sha256":digest(first)}
    validate(REPORT_SCHEMA,output); print(json.dumps(output,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
