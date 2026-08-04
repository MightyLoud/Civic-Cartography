# Production Batch 1 — Washington Wave D acceptance

Wave D executes the fourth 20 frozen Washington municipal targets from issue #112: WA-PB01-061 through WA-PB01-080, Nooksack through Pe Ell.

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
- Overall Wave D gate: **passed**

Evaluation ID: `723b9ea9d19a58f55574`

Run ID: `0f66c79b81482f1fa935`

## Reproducibility

The workflow selects Wave D deterministically from the merged 100-target manifest and performs two clean captures at `2026-08-04T13:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30915040910` produced artifact `8894714672` with digest `sha256:8a0fd7b8254462fae5937a5df067ae0a54ebb705a810bcb4ff22c4e624c4e765`.

## Reusable execution

Wave D passed through the reusable production-wave evaluator established by Wave A and reused by Waves B and C. No target identity, selector, classification rule, generator implementation, authoritative override, canonical alias, or frozen Batch Pilot target changed.

## Regression protection

The Wave D workflow runs the frozen Batch Pilot 25 in parallel. The shared production-wave test change also reruns Waves A, B, and C independently, preserving all four completed production waves on the same final head.
