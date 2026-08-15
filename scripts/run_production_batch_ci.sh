#!/usr/bin/env bash
set -euo pipefail

: "${UPSTREAM_REPOSITORY:?UPSTREAM_REPOSITORY is required}"
: "${UPSTREAM_REVISION:?UPSTREAM_REVISION is required}"
: "${RUN_ASOF:?RUN_ASOF is required}"
: "${FULL_MANIFEST:?FULL_MANIFEST is required}"
: "${WAVE:?WAVE is required}"
: "${EXPECTED_TARGET_COUNT:?EXPECTED_TARGET_COUNT is required}"
: "${CROSSWALK:?CROSSWALK is required}"
: "${PATCH_1:?PATCH_1 is required}"
: "${PATCH_2:?PATCH_2 is required}"
: "${PATCH_3:?PATCH_3 is required}"
: "${PATCH_4:?PATCH_4 is required}"
: "${OVERRIDE_REGISTRY:?OVERRIDE_REGISTRY is required}"
: "${ALIAS_REGISTRY:?ALIAS_REGISTRY is required}"

BUILD_ROOT="${BUILD_ROOT:-build/generic-production}"
WAVE_MANIFEST="$BUILD_ROOT/wave-manifest.yml"
ACCEPTANCE="$BUILD_ROOT/acceptance.json"

rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT"

python -m pytest \
  tests/test_target_manifest.py \
  tests/test_production_wave.py \
  tests/test_batch_capture.py \
  tests/test_authoritative_overrides.py \
  tests/test_canonical_aliases.py \
  tests/test_canonical_alias_acceptance.py \
  --color=yes

python scripts/run_production_batch.py \
  --manifest "$FULL_MANIFEST" \
  --wave "$WAVE" \
  --expected-target-count "$EXPECTED_TARGET_COUNT" \
  --result-path "$WAVE_MANIFEST"

python -m pip install uv
(
  cd upstream
  uv sync --frozen
)

# Apply the same validated generator fixes used by the frozen WA production gate.
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

capture_run() {
  local run_name="$1"
  local run_dir="$BUILD_ROOT/$run_name"

  PYTHONPATH=. upstream/.venv/bin/python scripts/capture_upstream_batch_with_overrides.py \
    --override-registry "$OVERRIDE_REGISTRY" \
    --alias-registry "$ALIAS_REGISTRY" \
    --upstream-root upstream \
    --target-manifest "$WAVE_MANIFEST" \
    --run-asof "$RUN_ASOF" \
    --source-dir "$BUILD_ROOT/upstream-source" \
    --work-dir "$run_dir" \
    --execution-results "$run_dir/execution-results.json" \
    --diagnostics "$run_dir/diagnostics.json"

  python scripts/normalize_capture_acceptance.py \
    --target-manifest "$WAVE_MANIFEST" \
    --execution-results "$run_dir/execution-results.json" \
    --diagnostics "$run_dir/diagnostics.json"

  PYTHONPATH=. python scripts/normalize_canonical_alias_acceptance.py \
    --alias-registry "$ALIAS_REGISTRY" \
    --target-manifest "$WAVE_MANIFEST" \
    --execution-results "$run_dir/execution-results.json" \
    --diagnostics "$run_dir/diagnostics.json"

  python scripts/run_target_manifest.py \
    --target-manifest "$WAVE_MANIFEST" \
    --run-asof "$RUN_ASOF" \
    --execution-results "$run_dir/execution-results.json" \
    --artifact-root "$run_dir/artifacts" \
    --result-path "$run_dir/report.json"

  python scripts/inventory_production_artifacts.py \
    --artifact-root "$run_dir/artifacts" \
    --report "$run_dir/report.json" \
    --result-path "$run_dir/artifact-inventory.json"
}

capture_run run-1
capture_run run-2

python scripts/check_production_wave.py \
  --target-manifest "$WAVE_MANIFEST" \
  --first-report "$BUILD_ROOT/run-1/report.json" \
  --second-report "$BUILD_ROOT/run-2/report.json" \
  --selection-crosswalk "$CROSSWALK" \
  --first-artifact-inventory "$BUILD_ROOT/run-1/artifact-inventory.json" \
  --second-artifact-inventory "$BUILD_ROOT/run-2/artifact-inventory.json" \
  --upstream-repository "$UPSTREAM_REPOSITORY" \
  --upstream-revision "$UPSTREAM_REVISION" \
  --expected-target-count "$EXPECTED_TARGET_COUNT" \
  --target-only-patch-count 0 \
  --result-path "$ACCEPTANCE"

python - "$ACCEPTANCE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
report = json.loads(path.read_text(encoding="utf-8"))
summary = report["summary"]
print(
    "production acceptance: "
    f"passed={summary['passed_count']}/{summary['target_count']} "
    f"deterministic={summary['deterministic_count']}/{summary['target_count']} "
    f"nesting={summary['nesting_parity_count']}/{summary['target_count']} "
    f"gate_passed={summary['gate_passed']}"
)
if not summary["gate_passed"]:
    raise SystemExit(1)
PY
