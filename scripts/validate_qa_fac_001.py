#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

FIXTURE = Path('tests/fixtures/qa_fac_001_outcome_matrix.json')


def derive_status(case):
    statuses = [v['status'] for v in case['checks'].values()]
    statuses += [v['status'] for v in case.get('domain_checks', [])]
    if 'FAIL' in statuses:
        return 'FAIL'
    if 'REVIEW' in statuses:
        return 'REVIEW'
    return 'PASS'


def canonical_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def main():
    cases = json.loads(FIXTURE.read_text())
    assert len(cases) == 5, f'expected 5 cases, got {len(cases)}'
    gate_ids = [c['gate_id'] for c in cases]
    assert len(gate_ids) == len(set(gate_ids)), 'duplicate gate_id'

    reports = []
    for case in cases:
        assert set(case['checks']) == {f'Q{i:02d}' for i in range(1, 11)}
        observed = derive_status(case)
        assert observed == case['expected_status'], (
            f"{case['gate_id']}: expected {case['expected_status']}, got {observed}"
        )
        reports.append({
            'gate_id': case['gate_id'],
            'domain': case['domain'],
            'status': observed,
            'checks_total': 10 + len(case.get('domain_checks', [])),
            'checks_passed': sum(
                1 for v in list(case['checks'].values()) + case.get('domain_checks', [])
                if v['status'] == 'PASS'
            ),
            'errors': [
                v['detail'] for v in list(case['checks'].values()) + case.get('domain_checks', [])
                if v['status'] == 'FAIL'
            ],
            'warnings': [
                v['detail'] for v in list(case['checks'].values()) + case.get('domain_checks', [])
                if v['status'] == 'REVIEW'
            ],
            'release_eligible': observed == 'PASS',
        })

    first = canonical_hash(reports)
    second = canonical_hash(json.loads(json.dumps(reports)))
    assert first == second, 'QA report hash is not deterministic'
    assert sum(r['status'] == 'PASS' for r in reports) == 4
    assert sum(r['status'] == 'FAIL' for r in reports) == 1
    assert next(r for r in reports if r['gate_id'].endswith('ANGELS-STUB-REGRESSION'))['status'] == 'FAIL'

    print(json.dumps({
        'status': 'PASS',
        'cases': len(reports),
        'pass_cases': 4,
        'fail_closed_cases': 1,
        'report_sha256': first,
        'reports': reports,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
