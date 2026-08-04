from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from civic_cartography.production_rollup import build_production_batch_rollup


ROOT = Path(__file__).resolve().parents[1]
WAVE_PATHS = [
    Path(
        f"evidence/production-batch-wa-100/wave-{letter.lower()}/"
        f"{'2026-08-03' if letter in 'AB' else '2026-08-04'}/"
        f"wave-{letter.lower()}-acceptance.json"
    )
    for letter in "ABCDE"
]
ROLLUP_PATH = Path(
    "evidence/production-batch-wa-100/closeout/2026-08-04/"
    "production-batch-wa-100-rollup.json"
)
SCHEMA_PATH = ROOT / "schemas" / "production-batch-rollup.schema.json"


def test_production_batch_rollup_passes_all_100_target_gates() -> None:
    rollup = build_production_batch_rollup(WAVE_PATHS)

    assert rollup["summary"] == {
        "wave_count": 5,
        "target_count": 100,
        "passed_count": 100,
        "deterministic_count": 100,
        "nesting_parity_count": 100,
        "target_artifact_count": 200,
        "wave_scoped_shared_artifact_count": 10,
        "artifact_hash_count": 210,
        "exception_or_review_count": 0,
        "target_only_patch_count": 0,
        "gate_passed": True,
    }
    assert all(rollup["criteria"].values())
    assert [target["target_id"] for target in rollup["targets"]] == [
        f"WA-PB01-{number:03d}" for number in range(1, 101)
    ]


def test_committed_rollup_is_reproducible_and_schema_valid() -> None:
    expected = build_production_batch_rollup(WAVE_PATHS)
    committed = json.loads(ROLLUP_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert committed == expected
    Draft202012Validator(schema).validate(committed)


def test_rollup_gate_rejects_duplicate_or_missing_target(tmp_path: Path) -> None:
    copied_paths: list[Path] = []
    for index, source in enumerate(WAVE_PATHS):
        data = json.loads(source.read_text(encoding="utf-8"))
        if index == 4:
            data = copy.deepcopy(data)
            data["targets"][-1]["target_id"] = "WA-PB01-099"
        destination = tmp_path / source.name
        destination.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        copied_paths.append(destination)

    rollup = build_production_batch_rollup(copied_paths)

    assert rollup["criteria"]["complete_target_id_coverage"] is False
    assert rollup["criteria"]["no_duplicate_target_ids"] is False
    assert rollup["summary"]["gate_passed"] is False
