# Batch Pilot 25 Acceptance

Verified on 2026-08-02 against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

## Result

- 25/25 targets emitted exactly one result.
- 6/6 regression fixtures passed.
- 12/15 known-archetype targets classified automatically (80.0%).
- 12/15 known-archetype targets generated YAML automatically (80.0%).
- 25/25 targets were deterministic across two runs.
- Complete reports were identical.
- Every unresolved target had an explicit exception class and review reason.
- Median recorded human review time was 0.0 minutes.
- Target-only production patch count was zero.
- Overall acceptance gate passed.

Evaluation ID: `03254d526d05fab00c78`  
Run ID: `b2db2dd876bd307d30af`

## Known-archetype exceptions

- BP25-012 — Miami-Dade County: exact OCDID not present in the matched or orphan inputs.
- BP25-015 — Denver Public Schools: maintained exact-name lookup did not resolve.
- BP25-016 — Seattle Public Schools: maintained exact-name lookup did not resolve.

These three explicit exceptions leave 12 of 15 known-archetype targets accepted, exactly meeting the 80% threshold.

## Discovery outcomes

The four discovery targets remained explicit `upstream_target_not_found` results:

- Bay Area Rapid Transit District
- Metropolitan Water Reclamation District of Greater Chicago
- Port of Seattle
- Metropolitan Government of Nashville and Davidson County

Discovery outcomes are retained for follow-on archetype work and do not count against the known-archetype threshold.

## Reproducibility

The batch runner derives all 14 states from the manifest, normalizes variable-width and optional-header state-local CSV files to the upstream `id,name` contract, applies the four validated upstream patches, and captures the complete manifest twice with one fixed timestamp.
