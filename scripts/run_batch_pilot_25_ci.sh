#!/usr/bin/env bash
set -euo pipefail

: "${UPSTREAM_REPOSITORY:?UPSTREAM_REPOSITORY is required}"
: "${UPSTREAM_REVISION:?UPSTREAM_REVISION is required}"
: "${RUN_ASOF:?RUN_ASOF is required}"
: "${PATCH_1:?PATCH_1 is required}"
: "${PATCH_2:?PATCH_2 is required}"
: "${PATCH_3:?PATCH_3 is required}"
: "${PATCH_4:?PATCH_4 is required}"
: "${OVERRIDE_REGISTRY:?OVERRIDE_REGISTRY is required}"
: "${ALIAS_REGISTRY:?ALIAS_REGISTRY is required}"

MANIFEST="tests/fixtures/batch_pilot_25.yml"

python -m pytest \
  tests/test_batch_acceptance.py \
  tests/test_authoritative_overrides.py \
  tests/test_canonical_aliases.py \
  tests/test_canonical_alias_acceptance.py \
  tests/test_capture_acceptance.py \
  --color=yes

python -m pip install uv
(
  cd upstream
  uv sync --frozen
)

PYTHONPATH=. upstream/.venv/bin/python -m pytest \
  tests/test_batch_capture.py \
  --color=yes

git -C upstream apply --check "../$PATCH_1"
git -C upstream apply "../$PATCH_1"
git -C upstream apply --check "../$PATCH_2"
git -C upstream apply "../$PATCH_2"
git -C upstream apply --check "../$PATCH_3"
git -C upstream apply "../$PATCH_3"
git -C upstream add -A
git -C upstream \
  -c user.name="Civic Cartography" \
  -c user.email="civic-cartography@example.invalid" \
  commit -m "Apply validated upstream fixes 1-3"

git -C upstream apply --check "../$PATCH_4"
git -C upstream apply "../$PATCH_4"
git -C upstream add -N .
git -C upstream diff --check
git -C upstream diff --binary > build-normalized-patch-4.patch
cmp "$PATCH_4" build-normalized-patch-4.patch

(
  cd upstream
  uv run pytest \
    tests/src/init_migration/test_generate_pipeline_stub_classification.py \
    tests/src/init_migration/test_jurisdiction_seed.py \
    tests/src/init_migration/test_authoritative_jurisdiction_override.py \
    tests/src/init_migration/test_canonical_alias_generation.py \
    --color=yes
  uv run ruff check \
    src/init_migration/pipeline_models.py \
    src/init_migration/generate_pipeline.py \
    src/init_migration/generate_division.py \
    src/init_migration/generate_jurisdiction.py \
    tests/src/init_migration/test_authoritative_jurisdiction_override.py \
    tests/src/init_migration/test_canonical_alias_generation.py
)

capture_run() {
  local run_dir="$1"
  PYTHONPATH=. upstream/.venv/bin/python scripts/capture_upstream_batch_with_overrides.py \
    --override-registry "$OVERRIDE_REGISTRY" \
    --alias-registry "$ALIAS_REGISTRY" \
    --upstream-root upstream \
    --target-manifest "$MANIFEST" \
    --run-asof "$RUN_ASOF" \
    --source-dir build/upstream-source \
    --work-dir "build/$run_dir" \
    --execution-results "build/$run_dir/execution-results.json" \
    --diagnostics "build/$run_dir/diagnostics.json"

  python scripts/normalize_capture_acceptance.py \
    --target-manifest "$MANIFEST" \
    --execution-results "build/$run_dir/execution-results.json" \
    --diagnostics "build/$run_dir/diagnostics.json"

  PYTHONPATH=. python scripts/normalize_canonical_alias_acceptance.py \
    --alias-registry "$ALIAS_REGISTRY" \
    --target-manifest "$MANIFEST" \
    --execution-results "build/$run_dir/execution-results.json" \
    --diagnostics "build/$run_dir/diagnostics.json"

  python scripts/run_target_manifest.py \
    --target-manifest "$MANIFEST" \
    --run-asof "$RUN_ASOF" \
    --execution-results "build/$run_dir/execution-results.json" \
    --artifact-root "build/$run_dir/artifacts" \
    --result-path "build/$run_dir/report.json"
}

capture_run run-1
capture_run run-2

set +e
PYTHONPATH=. python scripts/check_batch_acceptance.py \
  --target-manifest "$MANIFEST" \
  --first-report build/run-1/report.json \
  --second-report build/run-2/report.json \
  --upstream-repository "$UPSTREAM_REPOSITORY" \
  --upstream-revision "$UPSTREAM_REVISION" \
  --target-only-patch-count 0 \
  --result-path build/batch-acceptance.json
acceptance_status=$?
set -e

python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("build/batch-acceptance.json").read_text())
summary = report["summary"]
criteria = report["criteria"]
lines = [
    "## Batch Pilot 25 acceptance",
    "",
    f"- Targets reported: **{summary['target_count']}/25**",
    f"- Known archetypes classified: **{summary['known_classified_count']}/15** ({summary['known_classification_rate']:.1%})",
    f"- Known archetypes generated: **{summary['known_generated_count']}/15** ({summary['known_generation_rate']:.1%})",
    f"- Deterministic targets: **{summary['deterministic_count']}/25**",
    f"- Reports identical: **{summary['reports_identical']}**",
    f"- Explicit-exception failures: **{summary['exception_failure_count']}**",
    f"- Median human minutes: **{summary['median_human_minutes']}**",
    f"- Overall gate passed: **{summary['gate_passed']}**",
    "",
    "| Criterion | Passed |",
    "|---|---|",
]
lines.extend(f"| {name} | {passed} |" for name, passed in criteria.items())
Path("batch-pilot-summary.md").write_text("\n".join(lines) + "\n")
PY

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat batch-pilot-summary.md >> "$GITHUB_STEP_SUMMARY"
fi

exit "$acceptance_status"
