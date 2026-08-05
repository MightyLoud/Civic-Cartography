# Production Batch 2 — Washington Wave C acceptance

Wave C executes the third 20 frozen Washington municipal targets from issue #134: WA-PB02-041 through WA-PB02-060, Union Gap through Woodinville.

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
- Overall Wave C gate: **passed**

Evaluation ID: `a810b4ee63faa9ee6007`

Run ID: `cef6e1399e1ca6a135d9`

## Reproducibility

The workflow selects Wave C deterministically from the frozen 65-target manifest and performs two clean captures at `2026-08-04T18:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30972453141` produced artifact `8917037517` with digest `sha256:b9cafe2966e4e3abd6d6513f1c1e9e0275e9789597642f1aceb9eb000706511a`.

## Regression protection

The Wave C workflow reruns the frozen Batch Pilot 25 in parallel. The shared PB02 workflow/runner guard also verifies that Waves A, B, and C invoke only their matching runners.
