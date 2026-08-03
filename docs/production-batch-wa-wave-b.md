# Production Batch 1 — Washington Wave B acceptance

Wave B executes the second 20 frozen Washington municipal targets from issue #112: WA-PB01-021 through WA-PB01-040, Latah through Mercer Island.

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
- Overall Wave B gate: **passed**

Evaluation ID: `d65b1634e7b02d1fe0b5`

Run ID: `bece54b9e87136456a55`

## Reproducibility

The workflow selects Wave B deterministically from the merged 100-target manifest and performs two clean captures at `2026-08-03T20:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30845399688` produced artifact `8868495903` with digest `sha256:a85093741349a93a72ab6ce26dad22a95ee0c8d2cf46c731801f5d011dfc39a6`.

## Reusable execution

Wave B passed through the reusable production-wave evaluator established by Wave A. No target identity, selector, classification rule, generator implementation, authoritative override, canonical alias, or frozen Batch Pilot target changed.

## Regression protection

The Wave B workflow runs the frozen Batch Pilot 25 in parallel. The shared production-wave test change also reran Wave A independently, and both regression paths passed on the implementation head.
