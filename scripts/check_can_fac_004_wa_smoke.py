#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CORE=json.loads((ROOT/'evidence/candidate-factory-wa-smoke/can-fac-004-snoqualmie.json').read_text())
EVID=json.loads((ROOT/'evidence/candidate-factory-wa-smoke/can-fac-004-source-evidence.json').read_text())
def fail(m): raise SystemExit('FAIL: '+m)
source_ids=set(); hashes=[]
for r in CORE['source_records']:
 d=hashlib.sha256(r['raw_payload_json'].encode()).hexdigest()
 if d!=r['raw_row_sha256'] or r['source_record_id']!='sr-wa-'+d: fail('source hash/id mismatch')
 source_ids.add(r['source_record_id']); hashes.append(d)
if len(set(hashes))!=4: fail('duplicate source hashes')
contests={r['contest_id']:r for r in CORE['contests']}; persons={r['person_id'] for r in CORE['persons']}; cands={r['candidacy_id']:r for r in CORE['candidacies']}
if CORE['election']['administering_jurisdiction_id']!='jurisdiction-wa-snoqualmie': fail('jurisdiction mismatch')
valid={'office-wa-snoqualmie-mayor','office-wa-snoqualmie-position-1'}
for c in contests.values():
 if c['office_id'] not in valid or c['expected_seats']!=1: fail('contest office mismatch')
for c in cands.values():
 if c['person_id'] not in persons or c['contest_id'] not in contests or c['primary_source_record_id'] not in source_ids: fail('orphan candidacy')
 if c['party_affiliation_raw'] or c['incumbent_status']!='Unknown': fail('unsupported inference')
ev={r['source_evidence_id'] for r in EVID['source_evidence']}; linked=set()
for l in EVID['evidence_links']:
 if l['source_evidence_id'] not in ev or l['target_id'] not in cands: fail('orphan evidence')
 linked.add(l['target_id'])
if linked!=set(cands): fail('missing candidacy evidence')
print('CAN-FAC-004 PASS: 1 election, 2 contests, 4 candidacies, 4 source hashes, 4 evidence links')
