# Production Batch 2 — Washington Wave A acceptance

Wave A executes the first 20 frozen Washington municipal targets from issue #134: WA-PB02-001 through WA-PB02-020, Roslyn through Spangle.

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

Evaluation ID: `8095aa8551f6d4b2fbfc`

Run ID: `66ebc145fbeb08918a18`

## Reproducibility

The workflow selects Wave A deterministically from the frozen 65-target manifest and performs two clean captures at `2026-08-04T18:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30948420301` produced artifact `8908110725` with digest `sha256:9b4450d89defd3c62c337bc9ad9cd7b4f00880ddc14ea9a176a923be976936a7`.

## QA correction

The first successful artifact generated the correct PB02 targets but inherited the hard-coded `WA-PB01` acceptance label. Artifact review caught the mismatch before permanent evidence was committed. The acceptance evaluator now derives the batch identity from the wave, enforces crosswalk and target-ID parity, and validates PB02 reports against the shared schema.

## Regression protection

The Wave A workflow runs the frozen Batch Pilot 25 in parallel. Changes to the shared production-wave evaluator also rerun all five completed PB01 waves, preserving the prior 100-target batch on the same head.
