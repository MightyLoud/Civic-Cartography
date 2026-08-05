from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


class ProductionRollupError(ValueError):
    """Raised when production-wave evidence cannot form a valid batch roll-up."""


REQUIRED_WAVE_CRITERIA = {
    "all_generated_artifacts_have_sha256",
    "all_nesting_relationships_preserved_as_lists",
    "all_output_paths_are_unique",
    "all_targets_are_deterministic",
    "all_targets_have_one_result_per_run",
    "all_targets_resolve_classify_and_generate",
    "artifact_inventories_are_identical",
    "target_crosswalk_parity",
    "zero_target_only_production_patches",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rollup_id(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def build_production_batch_rollup(
    acceptance_paths: Iterable[str | Path],
    *,
    batch_id: str = "WA-PB01",
    expected_target_count: int = 100,
    expected_wave_letters: str = "ABCDE",
) -> dict[str, object]:
    paths = [Path(path) for path in acceptance_paths]
    if not paths:
        raise ProductionRollupError("at least one wave acceptance path is required")

    if (
        not expected_wave_letters
        or not expected_wave_letters.isalpha()
        or not expected_wave_letters.isupper()
        or len(set(expected_wave_letters)) != len(expected_wave_letters)
    ):
        raise ProductionRollupError(
            "expected_wave_letters must contain unique uppercase letters"
        )

    expected_waves = [
        f"{batch_id}-{letter}" for letter in expected_wave_letters
    ]
    expected_target_ids = [
        f"{batch_id}-{number:03d}"
        for number in range(1, expected_target_count + 1)
    ]

    wave_records: list[dict[str, object]] = []
    targets: list[dict[str, object]] = []
    target_ids: list[str] = []
    target_output_paths: list[str] = []
    crosswalk_hashes: set[str] = set()
    upstream_pairs: set[tuple[str, str]] = set()

    all_wave_gates_pass = True
    all_wave_criteria_pass = True
    all_inventories_identical = True
    all_exact_identifiers = True
    all_classifications_match = True
    all_generation_passes = True
    all_targets_deterministic = True
    all_nesting_parity = True
    all_artifacts_hashed = True
    no_exceptions_or_reviews = True
    exception_or_review_count = 0
    target_only_patch_count = 0

    for path in paths:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        wave = evidence["wave"]
        summary = evidence["summary"]
        criteria = evidence["criteria"]
        inventory = evidence["artifact_inventory"]
        wave_targets = evidence["targets"]

        missing_criteria = REQUIRED_WAVE_CRITERIA - set(criteria)
        if missing_criteria:
            raise ProductionRollupError(
                f"{wave} is missing criteria: {sorted(missing_criteria)}"
            )

        crosswalk_hashes.add(evidence["crosswalk_sha256"])
        upstream_pairs.add(
            (
                evidence["upstream"]["repository"],
                evidence["upstream"]["revision"],
            )
        )
        all_wave_gates_pass &= summary["gate_passed"] is True
        all_wave_criteria_pass &= all(criteria.values())
        target_only_patch_count += summary["target_only_patch_count"]
        all_inventories_identical &= (
            summary["artifact_inventories_identical"] is True
            and inventory["identical"] is True
            and inventory["first_inventory_sha256"]
            == inventory["second_inventory_sha256"]
        )

        for target in wave_targets:
            target_id = target["target_id"]
            output_hashes = target["output_hashes"]
            target_ids.append(target_id)
            target_output_paths.extend(output_hashes)
            all_exact_identifiers &= target["resolved_ocdids"] == [
                target["maintained_ocdid"]
            ]
            all_classifications_match &= (
                target["inferred_classification"] == "government"
            )
            all_generation_passes &= (
                target["generation_status"] == "generated"
                and target["status"] == "passed"
            )
            all_targets_deterministic &= target["deterministic"] is True
            all_nesting_parity &= target["nesting_parity"] is True
            all_artifacts_hashed &= (
                len(output_hashes) == 2
                and all(
                    isinstance(digest, str)
                    and len(digest) == 64
                    and all(char in "0123456789abcdef" for char in digest)
                    for digest in output_hashes.values()
                )
            )
            no_exceptions_or_reviews &= (
                target["exception_class"] is None
                and target["review_reason"] is None
                and not target["failures"]
            )
            if (
                target["exception_class"] is not None
                or target["review_reason"] is not None
                or target["failures"]
            ):
                exception_or_review_count += 1
            targets.append(
                {
                    "target_id": target_id,
                    "wave": target["wave"],
                    "census_geoid": target["census_geoid"],
                    "jurisdiction_name": target["jurisdiction_name"],
                    "maintained_ocdid": target["maintained_ocdid"],
                    "status": target["status"],
                }
            )

        recorded_path = path.as_posix() if not path.is_absolute() else path.name
        wave_records.append(
            {
                "wave": wave,
                "acceptance_path": recorded_path,
                "acceptance_sha256": _sha256(path),
                "evaluation_id": evidence["evaluation_id"],
                "run_asof": evidence["run_asof"],
                "run_id": evidence["first_run_id"],
                "target_count": summary["target_count"],
                "passed_count": summary["passed_count"],
                "deterministic_count": summary["deterministic_count"],
                "nesting_parity_count": summary["nesting_parity_count"],
                "artifact_count": summary["artifact_count"],
                "target_artifact_count": summary["target_artifact_count"],
                "shared_artifact_count": summary["shared_artifact_count"],
                "inventory_sha256": inventory["first_inventory_sha256"],
                "gate_passed": summary["gate_passed"],
            }
        )

    wave_records.sort(key=lambda item: item["wave"])
    targets.sort(key=lambda item: item["target_id"])

    duplicate_target_ids = len(target_ids) != len(set(target_ids))
    duplicate_target_output_paths = len(target_output_paths) != len(
        set(target_output_paths)
    )
    wave_coverage_criterion = (
        "all_five_waves_present"
        if expected_wave_letters == "ABCDE"
        else "all_expected_waves_present"
    )
    criteria = {
        wave_coverage_criterion: [
            wave["wave"] for wave in wave_records
        ]
        == expected_waves,
        "all_wave_gates_pass": all_wave_gates_pass,
        "all_wave_criteria_pass": all_wave_criteria_pass,
        "complete_target_id_coverage": sorted(target_ids)
        == expected_target_ids,
        "no_duplicate_target_ids": not duplicate_target_ids,
        "all_targets_resolve_by_exact_maintained_ocdid": all_exact_identifiers,
        "all_targets_match_government_classification": all_classifications_match,
        "all_targets_generate_division_and_jurisdiction": all_generation_passes,
        "all_targets_are_deterministic": all_targets_deterministic,
        "all_nesting_relationships_preserved_as_lists": all_nesting_parity,
        "all_target_artifacts_have_sha256": all_artifacts_hashed,
        "all_target_output_paths_are_unique": not duplicate_target_output_paths,
        "all_wave_artifact_inventories_are_identical": all_inventories_identical,
        "all_waves_share_one_selection_crosswalk": len(crosswalk_hashes) == 1,
        "all_waves_share_one_upstream_revision": len(upstream_pairs) == 1,
        "no_exceptions_or_review_reasons": no_exceptions_or_reviews,
        "zero_target_only_production_patches": target_only_patch_count == 0,
    }

    payload: dict[str, object] = {
        "schema_version": 1,
        "batch_id": batch_id,
        "crosswalk_sha256": next(iter(crosswalk_hashes))
        if len(crosswalk_hashes) == 1
        else None,
        "upstream": (
            {
                "repository": next(iter(upstream_pairs))[0],
                "revision": next(iter(upstream_pairs))[1],
            }
            if len(upstream_pairs) == 1
            else None
        ),
        "summary": {
            "wave_count": len(wave_records),
            "target_count": len(target_ids),
            "passed_count": sum(wave["passed_count"] for wave in wave_records),
            "deterministic_count": sum(
                wave["deterministic_count"] for wave in wave_records
            ),
            "nesting_parity_count": sum(
                wave["nesting_parity_count"] for wave in wave_records
            ),
            "target_artifact_count": sum(
                wave["target_artifact_count"] for wave in wave_records
            ),
            "wave_scoped_shared_artifact_count": sum(
                wave["shared_artifact_count"] for wave in wave_records
            ),
            "artifact_hash_count": sum(
                wave["artifact_count"] for wave in wave_records
            ),
            "exception_or_review_count": exception_or_review_count,
            "target_only_patch_count": target_only_patch_count,
            "gate_passed": all(criteria.values()),
        },
        "criteria": criteria,
        "waves": wave_records,
        "targets": targets,
    }
    payload["rollup_id"] = _rollup_id(payload)
    return payload
