#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

FIXTURE = Path('tests/fixtures/orch_fac_007_events.json')
ALLOWED = {'READY','DISPATCH','LOCK_ACQUIRED','STAGE_START','STAGE_COMPLETE','REVIEW','FAIL','RETRY','LOCK_RELEASED','PROMOTION_READY','HANDOFF'}


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def replay(case):
    seen_events, seen_keys = set(), set()
    events=[]
    state='BLOCKED'; lock='RELEASED'; promotion=False; last_seq=0; ok=True
    for raw in case['events']:
        eid, key = raw['event_id'], raw['idempotency_key']
        if eid in seen_events or key in seen_keys:
            continue
        seen_events.add(eid); seen_keys.add(key)
        seq=raw['seq']
        if seq <= last_seq:
            ok=False
        last_seq=seq
        et=raw['event_type']
        if et not in ALLOWED:
            ok=False
        prev=raw.get('previous_state')
        nxt=raw.get('next_state')
        if prev is not None and prev != state:
            ok=False
        if et == 'LOCK_ACQUIRED':
            if lock == 'HELD': ok=False
            lock='HELD'
        elif et == 'LOCK_RELEASED':
            if lock != 'HELD': ok=False
            lock='RELEASED'
        elif et == 'PROMOTION_READY':
            promotion=True
        elif et == 'RETRY':
            promotion=False
        elif et == 'HANDOFF':
            if lock != 'RELEASED' or not promotion:
                ok=False
        if nxt is not None:
            state=nxt
        events.append(raw)
    result={'case_id':case['case_id'],'state':state,'lock':lock,'promotion_ready':promotion,'reconciliation':'PASS' if ok else 'FAIL','accepted_events':len(events)}
    exp=case['expected']
    for k,v in exp.items():
        if result[k] != v:
            raise AssertionError(f"{case['case_id']} {k}: got {result[k]!r}, expected {v!r}")
    return result


def main():
    data=json.loads(FIXTURE.read_text())
    a=[replay(c) for c in data['cases']]
    b=[replay(c) for c in data['cases']]
    h1,h2=canonical_hash(a),canonical_hash(b)
    if h1 != h2:
        raise AssertionError('audit replay not deterministic')
    print(json.dumps({'gate_id':'ORCH-FAC-007','status':'PASS','cases':len(a),'deterministic':True,'report_sha256':h1,'results':a}, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
