# Production Batch 1 — Washington Wave E acceptance

Wave E executes the final 20 frozen Washington municipal targets from issue #112: WA-PB01-081 through WA-PB01-100, Pomeroy through Rosalia.

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
- Overall Wave E gate: **passed**

Evaluation ID: `05a1a026787927c1f36a`

Run ID: `761e4fa9c2eda4a520e0`

## Reproducibility

The corrected workflow selects Wave E deterministically from the merged 100-target manifest and performs two clean captures at `2026-08-04T15:00:00Z` against `openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`.

Every file under each run's artifact root is inventoried. The 40 target files and two shared Washington stubs have matching paths and SHA-256 digests across both runs. The complete target reports are also identical.

GitHub Actions run `30920950306` produced artifact `8897073623` with digest `sha256:8de13cdb4527c6fefe7c60a2e955342301e900a456f62b643ce459e39a4fa934`.

## QA correction

The first workflow attempt carried a Wave E label but invoked the underscore-delimited Wave D runner path. Artifact inspection caught the mismatch before evidence was accepted. The workflow now invokes the Wave E runner, and a five-wave regression test enforces label-to-runner parity for Waves A–E.

## Regression protection

The Wave E workflow runs the frozen Batch Pilot 25 in parallel. The shared production-wave tests also rerun Waves A–D independently, preserving all five completed production waves on the same final head.
