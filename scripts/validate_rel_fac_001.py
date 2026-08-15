import hashlib
import json
from pathlib import Path

FIXTURE = Path('tests/fixtures/rel_fac_001_cases.json')


def derive(case):
    data = case['input']
    qa = data['qa_status']
    exceptions = data.get('exceptions', [])
    has_blocking = any(e.get('blocking') for e in exceptions if e.get('status') not in {'RESOLVED', 'CLOSED'})

    if qa == 'PASS' and not has_blocking:
        promotion_status = 'READY'
        promotion_eligible = True
    elif qa == 'REVIEW' and not has_blocking:
        promotion_status = 'QUEUED'
        promotion_eligible = False
    else:
        promotion_status = 'BLOCKED'
        promotion_eligible = False

    report = {
        'gate_id': data['gate_id'],
        'qa_status': qa,
        'promotion_status': promotion_status,
        'release_status': 'HOLD',
        'promotion_eligible': promotion_eligible,
        'release_eligible': False,
        'exceptions': exceptions,
    }
    return report


def canonical_hash(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


def main():
    cases = json.loads(FIXTURE.read_text())
    reports = []
    for case in cases:
        report = derive(case)
        expected = case['expected']
        for key, value in expected.items():
            assert report[key] == value, f"{case['name']}: {key} expected {value!r}, got {report[key]!r}"
        assert report['release_status'] != 'RELEASED', f"{case['name']}: release cannot happen automatically"
        reports.append(report)

    h1 = canonical_hash(reports)
    h2 = canonical_hash([derive(c) for c in cases])
    assert h1 == h2, 'deterministic report hash mismatch'
    assert len(reports) == 4
    assert reports[0]['promotion_status'] == 'READY'
    assert reports[1]['promotion_status'] == 'QUEUED'
    assert reports[2]['promotion_status'] == 'BLOCKED'
    assert reports[3]['promotion_status'] == 'BLOCKED'
    print(f'REL-FAC-001 PASS cases=4 sha256={h1}')


if __name__ == '__main__':
    main()
