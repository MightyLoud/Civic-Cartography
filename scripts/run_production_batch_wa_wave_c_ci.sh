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

FULL_MANIFEST="tests/fixtures/production_batch_wa_100.yml"
WAVE_MANIFEST="build/wa-pb01-wave-c-manifest.yml"
CROSSWALK="evidence/production-batch-wa-100/selection/selection-crosswalk.json"

python -m pytest \
  tests/test_target_manifest.py \
  tests/test_production_batch_wa_100_selection.py \
  tests/test_production_wave.py \
  tests/test_batch_capture.py \
  tests/test_authoritative_overrides.py \
  tests/test_canonical_aliases.py \
  tests/test_canonical_alias_acceptance.py \
  --color=yes

python scripts/select_production_wave.py \
  --target-manifest "$FULL_MANIFEST" \
  --wave WA-PB01-C \
  --expected-target-count 20 \
  --result-path "$WAVE_MANIFEST"

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
    --target-manifest "$WAVE_MANIFEST" \
    --run-asof "$RUN_ASOF" \
    --source-dir build/upstream-source \
    --work-dir "build/$run_dir" \
    --execution-results "build/$run_dir/execution-results.json" \
    --diagnostics "build/$run_dir/diagnostics.json"

  python scripts/normalize_capture_acceptance.py \
    --target-manifest "$WAVE_MANIFEST" \
    --execution-results "build/$run_dir/execution-results.json" \
    --diagnostics "build/$run_dir/diagnostics.json"

  PYTHONPATH=. python scripts/normalize_canonical_alias_acceptance.py \
    --alias-registry "$ALIAS_REGISTRY" \
    --target-manifest "$WAVE_MANIFEST" \
    --execution-results "build/$run_dir/execution-results.json" \
    --diagnostics "build/$run_dir/diagnostics.json"

  python scripts/run_target_manifest.py \
    --target-manifest "$WAVE_MANIFEST" \
    --run-asof "$RUN_ASOF" \
    --execution-results "build/$run_dir/execution-results.json" \
    --artifact-root "build/$run_dir/artifacts" \
    --result-path "build/$run_dir/report.json"

  python scripts/inventory_production_artifacts.py \
    --artifact-root "build/$run_dir/artifacts" \
    --report "build/$run_dir/report.json" \
    --result-path "build/$run_dir/artifact-inventory.json"
}

capture_run run-1
capture_run run-2

set +e
PYTHONPATH=. python scripts/check_production_wave.py \
  --target-manifest "$WAVE_MANIFEST" \
  --first-report build/run-1/report.json \
  --second-report build/run-2/report.json \
  --selection-crosswalk "$CROSSWALK" \
  --first-artifact-inventory build/run-1/artifact-inventory.json \
  --second-artifact-inventory build/run-2/artifact-inventory.json \
  --upstream-repository "$UPSTREAM_REPOSITORY" \
  --upstream-revision "$UPSTREAM_REVISION" \
  --expected-target-count 20 \
  --target-only-patch-count 0 \
  --result-path build/wa-pb01-wave-c-acceptance.json
acceptance_status=$?
set -e

python - <<'PY'
import json
from pathlib import Path

report = json.loads(Path("build/wa-pb01-wave-c-acceptance.json").read_text())
summary = report["summary"]
criteria = report["criteria"]
lines = [
    "## Production Batch 1 — Wave C",
    "",
    f"- Targets passed: **{summary['passed_count']}/{summary['target_count']}**",
    f"- Deterministic targets: **{summary['deterministic_count']}/{summary['target_count']}**",
    f"- Nesting parity: **{summary['nesting_parity_count']}/{summary['target_count']}**",
    f"- Reports identical: **{summary['reports_identical']}**",
    f"- Unique output paths: **{summary['unique_output_paths']}**",
    f"- Artifacts hashed: **{summary['artifact_count']}** ({summary['target_artifact_count']} target + {summary['shared_artifact_count']} shared)",
    f"- Artifact inventories identical: **{summary['artifact_inventories_identical']}**",
    f"- Target-only patches: **{summary['target_only_patch_count']}**",
    f"- Overall gate passed: **{summary['gate_passed']}**",
    "",
    "| Criterion | Passed |",
    "|---|---|",
]
lines.extend(f"| {name} | {passed} |" for name, passed in criteria.items())
Path("wa-pb01-wave-c-summary.md").write_text("\n".join(lines) + "\n")
PY

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat wa-pb01-wave-c-summary.md >> "$GITHUB_STEP_SUMMARY"
fi

exit "$acceptance_status"
