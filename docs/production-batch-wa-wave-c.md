# Production Batch 1 — Washington Wave C acceptance

Wave C executes the third 20 frozen Washington municipal targets from issue #112: WA-PB01-041 through WA-PB01-060, Mesa through Newport.

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

Evaluation ID: `f74a0997789659e39e64`

Run ID: `3b5a11e5bf9870f69730`

## Reproducibility

The workflow selects Wave C deterministically from the merged 100-target manifest and performs two clean captures at `2026-08-04T12:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30909906856` produced artifact `8892629139` with digest `sha256:7942b207b1784e77cc952c95087321a1b048617192cd57fee9d7edf651d8767b`.

## Reusable execution

Wave C passed through the reusable production-wave evaluator established by Wave A and reused by Wave B. No target identity, selector, classification rule, generator implementation, authoritative override, canonical alias, or frozen Batch Pilot target changed.

## Regression protection

The Wave C workflow runs the frozen Batch Pilot 25 in parallel. The shared production-wave test change also reruns Waves A and B independently, preserving all three completed production waves on the same final head.
