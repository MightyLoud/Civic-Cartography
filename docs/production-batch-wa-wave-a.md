# Production Batch 1 — Washington Wave A acceptance

Wave A executes the first 20 frozen Washington municipal targets from issue #112: WA-PB01-001 through WA-PB01-020, Ione through Langley.

## Final result

- Targets resolved, classified, and generated: **20/20**
- Exact maintained OCDID matches: **20/20**
- Classification: **government** for 20/20
- Generated target artifacts: **40** (20 Divisions + 20 Jurisdictions)
- Shared generated artifacts: **2** Washington ancestor stubs
- SHA-256 coverage: **42/42 artifacts**
- Deterministic targets: **20/20**
- Identical artifact inventories: **true**
- List-valued nesting parity: **20/20**
- Exceptions or review reasons: **0**
- Target-only production patches: **0**
- Overall Wave A gate: **passed**

Evaluation ID: `cd9fea3aad75dc97e7c4`

Run ID: `7ad97093b4ee98e829e8`

## Reproducibility

The workflow selects Wave A deterministically from the merged 100-target manifest and performs two clean captures at `2026-08-03T18:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30821256582` produced artifact `8858966463` with digest `sha256:eb87425af593b1fdf92c69dff85d1572a4c2e1669d664289bf6d9a20b6b7dda9`.

## Deterministic shared stubs

The first all-artifact gate exposed wall-clock timestamps in recursive ancestor stubs. The capture boundary now applies the explicit run timestamp to leaf Division generation, leaf Jurisdiction generation, and recursive ancestor-stub generation. No target identity, selector, classification rule, or generator output coordinate changed.

## Regression protection

The Wave A workflow runs the frozen Batch Pilot 25 in parallel. The final head also triggers the standalone Batch Pilot workflow, so production execution cannot silently regress the completed pilot contract.
