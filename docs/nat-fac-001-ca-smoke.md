# NAT-FAC-001 California portability smoke

Status: PASS
Run: GitHub Actions 31905012554 / ca-smoke
Run as of: 2026-08-15T19:40:00Z
Upstream: openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705

## Acceptance

- Targets passed: 5/5
- Deterministic targets: 5/5
- Nesting parity: 5/5
- Overall gate: PASS
- Artifacts per run: 12 (10 target + 2 shared)
- Uploaded evidence files: 35
- Artifact ID: 9252111845
- Artifact ZIP SHA-256: 934a1e1e3469d1b482971b85bbcaa873f043dc65293d6312b3564c8dc3a925e1

## Targets

- Los Angeles — 0644000 — ocd-division/country:us/state:ca/place:los_angeles
- San Diego — 0666000 — ocd-division/country:us/state:ca/place:san_diego
- Sacramento — 0664000 — ocd-division/country:us/state:ca/place:sacramento
- Fresno — 0627000 — ocd-division/country:us/state:ca/place:fresno
- Berkeley — 0606000 — ocd-division/country:us/state:ca/place:berkeley

## Boundary

This proves the existing production engine can execute a California Census-place manifest through the same capture, normalization, artifact hashing, second-run determinism, nesting parity, and acceptance contract used by the Washington production gate. It does not yet generalize non-place Census geographies; that remains a separate Oregon/county portability gate.
