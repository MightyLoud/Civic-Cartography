# Production Batch 1 — Washington 100-target closeout

Production Batch 1 covers 100 frozen active Washington municipal governments, WA-PB01-001 through WA-PB01-100, Ione through Rosalia.

## Machine-verified result

- Waves passed: **5/5**
- Targets resolved by exact maintained OCDID: **100/100**
- `government` classifications: **100/100**
- Division + Jurisdiction generation: **100/100**
- Deterministic targets across two captures per wave: **100/100**
- List-valued county/SLDU/SLDL nesting parity: **100/100**
- Target artifacts hashed: **200/200**
- Wave-scoped shared ancestor-stub hash entries: **10/10**
- Total artifact hash entries: **210/210**
- Exceptions or review reasons: **0**
- Target-only production patches: **0**
- Frozen Batch Pilot regression retained: **25/25**
- Regression fixtures retained: **6/6**

The 10 shared-artifact hash entries are the same two Washington ancestor-stub paths inventoried independently in each of the five waves; they are not ten unique shared files.

Roll-up ID: `4cc54ecf8306a400d5a9`

## Evidence chain

The final roll-up hashes and evaluates each committed wave acceptance record. Every wave uses the same selection crosswalk and pinned upstream revision:

`openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`

The roll-up enforces exact IDs 001–100, rejects duplicate or missing targets, verifies two target artifact hashes per jurisdiction, and requires every wave criterion and inventory gate to pass.

## Reusable corrections

Two system-level gaps were caught during production and fixed without changing target identities:

1. Wave A exposed wall-clock timestamps in recursive Washington ancestor stubs. The capture boundary now gives target and shared artifacts the same pinned run timestamp.
2. Wave E artifact inspection exposed a workflow label/runner mismatch. A five-wave regression now requires each workflow to invoke its matching runner.

## Release closeout

The repository evidence satisfies the internal 100-target completion contract. Final-head workflow status and the external operations-tracker update are recorded on PR #128 and issue #112 after the release head passes.
