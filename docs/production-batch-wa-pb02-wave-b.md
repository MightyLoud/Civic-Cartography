# Production Batch 2 — Washington Wave B acceptance

Wave B executes the second 20 frozen Washington municipal targets from issue #134: WA-PB02-021 through WA-PB02-040, Spokane Valley through Twisp.

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

Evaluation ID: `f86469f13042dfae479e`

Run ID: `b4a0660c14be4051ef71`

## Reproducibility

The workflow selects Wave B deterministically from the frozen 65-target manifest and performs two clean captures at `2026-08-04T18:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30970632202` produced artifact `8916385342` with digest `sha256:89d698a723be0454ba9df7354e694101e6a386c8b3d8c1e01a99b72ff9029805`.

## Regression protection

The Wave B workflow reruns the frozen Batch Pilot 25 in parallel. The shared PB02 workflow/runner guard also verifies that both Wave A and Wave B invoke only their matching runners.

