#!/usr/bin/env python3
import hashlib, json, pathlib, sys
from urllib.parse import urlparse

FIXTURE = pathlib.Path('tests/fixtures/src_fac_001_known_good_sources.json')
GOVERNED_ADAPTERS = {
 'ADP-WB027-001','ADP-WB027-002','ADP-WB027-003','ADP-WB027-016',
 'ADP-WB027-020','ADP-WB027-024','ADP-WB027-029'
}
OFFICIAL_SUFFIXES = (
 'elections.alaska.gov','elections.hawaii.gov','sos.oregon.gov',
 'sos.nm.gov','sos.wa.gov','elections.virginia.gov'
)

def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def validate(data):
    errors=[]
    cases=data.get('cases',[])
    if len(cases)!=10: errors.append(f'expected 10 cases, got {len(cases)}')
    ids=set()
    for case in cases:
        cid=case.get('case_id')
        if cid in ids: errors.append(f'duplicate case_id {cid}')
        ids.add(cid)
        if case.get('disposition') not in {'READY','REVIEW','BLOCKED'}: errors.append(f'{cid}: bad disposition')
        for src in case.get('candidate_sources',[]):
            host=(urlparse(src.get('url','')).hostname or '').lower()
            if not any(host==s or host.endswith('.'+s) for s in OFFICIAL_SUFFIXES): errors.append(f'{cid}: non-official host {host}')
            if src.get('authority_level')!='OFFICIAL': errors.append(f'{cid}: authority not OFFICIAL')
            if src.get('status') not in {'ACTIVE','STALE','BROKEN'}: errors.append(f'{cid}: bad source status')
            aid=src.get('adapter_id')
            if aid not in GOVERNED_ADAPTERS: errors.append(f'{cid}: ungoverned adapter {aid}')
            match=src.get('adapter_match')
            if match not in {'EXACT','LIKELY','NONE'}: errors.append(f'{cid}: bad adapter match')
            if match=='EXACT' and src.get('schema_fingerprint') in {'GUIDANCE_ONLY','DIRECTORY','LOCAL_ROUTING'}:
                errors.append(f'{cid}: unsupported EXACT match')
    return errors

def main():
    data=json.loads(FIXTURE.read_text())
    h1=canonical_hash(data)
    data2=json.loads(FIXTURE.read_text())
    h2=canonical_hash(data2)
    errors=validate(data)
    if h1!=h2: errors.append('determinism hash mismatch')
    print(f'cases={len(data.get("cases",[]))}')
    print(f'canonical_sha256={h1}')
    print(f'deterministic={h1==h2}')
    if errors:
        print('\n'.join('FAIL: '+e for e in errors)); return 1
    print('SRC-FAC-001 PASS')
    return 0

if __name__=='__main__': sys.exit(main())
