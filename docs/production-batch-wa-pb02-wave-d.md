# Production Batch 2 — Washington Wave D acceptance

Wave D executes the final five frozen Washington municipal targets from issue #134: WA-PB02-061 through WA-PB02-065, Woodland through Zillah.

## Final result

- Targets resolved, classified, and generated: **5/5**
- Exact maintained OCDID matches: **5/5**
- Classification: **government** for 5/5
- Generated target artifacts: **10** (5 Divisions + 5 Jurisdictions)
- Shared generated artifacts: **2** Washington ancestor stubs
- SHA-256 coverage: **12/12 artifacts**
- Deterministic targets: **5/5**
- Identical artifact inventories: **true**
- List-valued nesting parity: **5/5**
- Exceptions or review reasons: **0**
- Target-only production patches: **0**
- Overall Wave D gate: **passed**

Evaluation ID: `19f51f1c346f3011e982`

Run ID: `a786a6078806da7ec3c5`

## Reproducibility

The workflow selects Wave D deterministically from the frozen 65-target manifest and performs two clean captures at `2026-08-04T18:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 10 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30974442523` produced artifact `8917746098` with digest `sha256:64195fa9cb2f7d3f72f93549ad534937b4b6a71b5263c231c5501be1105b8821`.

## Regression protection

The Wave D workflow reruns the frozen Batch Pilot 25 in parallel. The shared PB02 workflow/runner guard verifies that Waves A through D invoke only their matching runners.
