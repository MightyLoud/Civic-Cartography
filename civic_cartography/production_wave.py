from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

import yaml

from civic_cartography.fixture_harness import (
    DETERMINISTIC_FIELDS,
    PASSING_MATCH_STATUSES,
    UPSTREAM_REVISION_PATTERN,
    load_result_report,
)
from civic_cartography.target_manifest import (
    Target,
    TargetManifest,
    load_manifest,
    manifest_to_dict,
)


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
NESTING_FIELDS = (
    "county_fips",
    "county_names",
    "sldu_fips",
    "sldl_fips",
)


class ProductionWaveError(ValueError):
    """Raised when production-wave evidence is malformed or incomplete."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def select_production_wave(
    manifest: TargetManifest,
    wave: str,
    *,
    expected_target_count: int = 20,
) -> TargetManifest:
    targets = tuple(target for target in manifest.targets if target.wave == wave)
    if len(targets) != expected_target_count:
        raise ProductionWaveError(
            f"{wave} must contain exactly {expected_target_count} targets, "
            f"found {len(targets)}"
        )
    if any(target.category != "production" for target in targets):
        raise ProductionWaveError(f"{wave} contains a non-production target")
    return replace(
        manifest,
        name=f"{manifest.name}_{wave.lower().replace('-', '_')}",
        description=f"{manifest.description or manifest.name} — {wave}",
        targets=targets,
    )


def write_wave_manifest(manifest: TargetManifest, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        key: value
        for key, value in manifest_to_dict(manifest).items()
        if value is not None
    }
    output.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def load_crosswalk(path: str | Path) -> dict[str, Any]:
    crosswalk_path = Path(path)
    try:
        raw = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProductionWaveError(f"selection crosswalk not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProductionWaveError(f"selection crosswalk is invalid JSON: {path}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("candidates"), list):
        raise ProductionWaveError("selection crosswalk must contain candidates")
    return raw


def _index_results(
    report: Mapping[str, Any], label: str
) -> dict[str, dict[str, Any]]:
    raw_results = report.get("results")
    if not isinstance(raw_results, list):
        raise ProductionWaveError(f"{label}.results must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_result in enumerate(raw_results):
        if not isinstance(raw_result, dict):
            raise ProductionWaveError(f"{label}.results[{index}] must be a mapping")
        target_id = raw_result.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise ProductionWaveError(
                f"{label}.results[{index}].target_id must be a string"
            )
        if target_id in indexed:
            raise ProductionWaveError(f"{label} contains duplicate {target_id}")
        indexed[target_id] = dict(raw_result)
    return indexed


def _crosswalk_index(
    crosswalk: Mapping[str, Any], wave: str
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for index, raw_row in enumerate(crosswalk["candidates"]):
        if not isinstance(raw_row, dict):
            raise ProductionWaveError(f"crosswalk.candidates[{index}] must be a mapping")
        if raw_row.get("disposition") != "target" or raw_row.get("wave") != wave:
            continue
        target_id = raw_row.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise ProductionWaveError(
                f"crosswalk.candidates[{index}].target_id must be a string"
            )
        if target_id in rows:
            raise ProductionWaveError(f"crosswalk contains duplicate {target_id}")
        rows[target_id] = dict(raw_row)
    return rows


def _nesting_failures(row: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    nesting = row.get("nesting")
    if not isinstance(nesting, dict):
        return ["selection crosswalk nesting must be a mapping"]
    for field in NESTING_FIELDS:
        value = nesting.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"nesting.{field} must be a non-empty list")
            continue
        if any(not isinstance(item, str) or not item for item in value):
            failures.append(f"nesting.{field} must contain non-empty strings")
        if len(set(value)) != len(value):
            failures.append(f"nesting.{field} must not contain duplicates")
    county_fips = nesting.get("county_fips")
    county_names = nesting.get("county_names")
    if isinstance(county_fips, list) and isinstance(county_names, list):
        if len(county_fips) != len(county_names):
            failures.append("county_fips and county_names lengths differ")
    for field in ("county_fips", "sldu_fips", "sldl_fips"):
        value = nesting.get(field)
        if isinstance(value, list) and any(
            not isinstance(item, str) or not re.fullmatch(r"[0-9]{3}", item)
            for item in value
        ):
            failures.append(f"nesting.{field} must contain three-digit FIPS codes")
    return failures


def _identity_failures(target: Target, row: Mapping[str, Any] | None) -> list[str]:
    if row is None:
        return ["selection crosswalk row is missing"]
    failures: list[str] = []
    expected = {
        "target_id": target.target_id,
        "display_name": target.jurisdiction_name,
        "census_geoid": target.census_geoid,
        "maintained_ocdid": target.selector.get("value"),
        "expected_classification": target.expected_classification,
        "wave": target.wave,
    }
    for field, value in expected.items():
        if row.get(field) != value:
            failures.append(
                f"selection crosswalk {field}={row.get(field)!r}; expected {value!r}"
            )
    failures.extend(_nesting_failures(row))
    return failures


def _result_failures(
    target: Target,
    result: Mapping[str, Any] | None,
    label: str,
) -> list[str]:
    if result is None:
        return [f"{label}: result is missing"]
    failures: list[str] = []
    expected_ocdid = target.selector.get("value")
    exact_fields = {
        "jurisdiction_name": target.jurisdiction_name,
        "category": "production",
        "census_geoid": target.census_geoid,
        "wave": target.wave,
        "expected_archetype": target.expected_archetype,
        "expected_classification": target.expected_classification,
        "requested_selector": target.selector,
    }
    for field, value in exact_fields.items():
        if result.get(field) != value:
            failures.append(f"{label}: {field} does not match the manifest")
    if result.get("resolved_ocdids") != [expected_ocdid]:
        failures.append(f"{label}: resolved_ocdids must equal the exact selector")
    if result.get("match_status") not in PASSING_MATCH_STATUSES:
        failures.append(f"{label}: match_status is not resolved")
    if result.get("inferred_classification") != target.expected_classification:
        failures.append(f"{label}: inferred classification does not match")
    if result.get("classification_status") != "matched":
        failures.append(f"{label}: classification_status must be matched")
    if result.get("generation_status") != "generated":
        failures.append(f"{label}: generation_status must be generated")

    division_paths = result.get("division_paths")
    jurisdiction_paths = result.get("jurisdiction_paths")
    if not isinstance(division_paths, list) or len(division_paths) != 1:
        failures.append(f"{label}: exactly one Division path is required")
    if not isinstance(jurisdiction_paths, list) or len(jurisdiction_paths) != 1:
        failures.append(f"{label}: exactly one Jurisdiction path is required")
    expected_paths = {
        str(path)
        for path in [
            *(division_paths if isinstance(division_paths, list) else []),
            *(jurisdiction_paths if isinstance(jurisdiction_paths, list) else []),
        ]
    }
    output_hashes = result.get("output_hashes")
    if not isinstance(output_hashes, dict) or set(output_hashes) != expected_paths:
        failures.append(f"{label}: output hashes must cover both artifacts exactly")
    elif any(
        not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest)
        for digest in output_hashes.values()
    ):
        failures.append(f"{label}: output hashes must be SHA-256 digests")
    if result.get("exception_class") is not None:
        failures.append(f"{label}: generated target retains an exception")
    if result.get("review_reason") not in (None, ""):
        failures.append(f"{label}: generated target retains a review reason")
    human_minutes = result.get("human_minutes")
    if (
        isinstance(human_minutes, bool)
        or not isinstance(human_minutes, (int, float))
        or human_minutes < 0
    ):
        failures.append(f"{label}: human_minutes must be non-negative")
    return failures


def _determinism_failures(
    first: Mapping[str, Any] | None,
    second: Mapping[str, Any] | None,
) -> list[str]:
    if first is None or second is None:
        return ["second_run: cannot compare a missing result"]
    return [
        f"second_run: {field} differs from first_run"
        for field in DETERMINISTIC_FIELDS
        if first.get(field) != second.get(field)
    ]


def evaluate_production_wave(
    manifest: TargetManifest,
    first_report: Mapping[str, Any],
    second_report: Mapping[str, Any],
    crosswalk: Mapping[str, Any],
    *,
    upstream_repository: str,
    upstream_revision: str,
    expected_target_count: int = 20,
    target_only_patch_count: int = 0,
) -> dict[str, Any]:
    if len(manifest.targets) != expected_target_count:
        raise ProductionWaveError(
            f"production wave must contain {expected_target_count} targets"
        )
    waves = {target.wave for target in manifest.targets}
    if len(waves) != 1 or None in waves:
        raise ProductionWaveError("production wave manifest must contain one wave")
    wave = next(iter(waves))
    if not UPSTREAM_REVISION_PATTERN.fullmatch(upstream_revision):
        raise ProductionWaveError("upstream revision must be a 40-character SHA")
    if isinstance(target_only_patch_count, bool) or target_only_patch_count < 0:
        raise ProductionWaveError("target_only_patch_count must be non-negative")

    manifest_sha = _sha256_value(manifest_to_dict(manifest))
    for label, report in (("first_report", first_report), ("second_report", second_report)):
        if report.get("manifest_name") != manifest.name:
            raise ProductionWaveError(f"{label}.manifest_name does not match")
        if report.get("manifest_sha256") != manifest_sha:
            raise ProductionWaveError(f"{label}.manifest_sha256 does not match")
    if first_report.get("run_asof") != second_report.get("run_asof"):
        raise ProductionWaveError("reports must use the same run_asof timestamp")

    first_by_id = _index_results(first_report, "first_report")
    second_by_id = _index_results(second_report, "second_report")
    crosswalk_by_id = _crosswalk_index(crosswalk, str(wave))
    expected_ids = {target.target_id for target in manifest.targets}

    outcomes: list[dict[str, Any]] = []
    all_paths: list[str] = []
    for target in manifest.targets:
        first = first_by_id.get(target.target_id)
        second = second_by_id.get(target.target_id)
        identity_failures = _identity_failures(
            target, crosswalk_by_id.get(target.target_id)
        )
        first_failures = _result_failures(target, first, "first_run")
        second_failures = _result_failures(target, second, "second_run")
        determinism_failures = _determinism_failures(first, second)
        failures = [
            *identity_failures,
            *first_failures,
            *second_failures,
            *determinism_failures,
        ]
        if first is not None:
            all_paths.extend(first.get("division_paths") or [])
            all_paths.extend(first.get("jurisdiction_paths") or [])
        reference = first or second or {}
        outcomes.append(
            {
                "target_id": target.target_id,
                "jurisdiction_name": target.jurisdiction_name,
                "census_geoid": target.census_geoid,
                "maintained_ocdid": target.selector.get("value"),
                "wave": target.wave,
                "status": "passed" if not failures else "failed",
                "deterministic": not determinism_failures,
                "nesting_parity": not identity_failures,
                "resolved_ocdids": reference.get("resolved_ocdids", []),
                "inferred_classification": reference.get("inferred_classification"),
                "generation_status": reference.get("generation_status"),
                "division_paths": reference.get("division_paths", []),
                "jurisdiction_paths": reference.get("jurisdiction_paths", []),
                "output_hashes": reference.get("output_hashes", {}),
                "exception_class": reference.get("exception_class"),
                "review_reason": reference.get("review_reason"),
                "failures": failures,
            }
        )

    first_parity = set(first_by_id) == expected_ids
    second_parity = set(second_by_id) == expected_ids
    crosswalk_parity = set(crosswalk_by_id) == expected_ids
    passed_count = sum(row["status"] == "passed" for row in outcomes)
    deterministic_count = sum(row["deterministic"] for row in outcomes)
    nesting_parity_count = sum(row["nesting_parity"] for row in outcomes)
    reports_identical = _sha256_value(first_report) == _sha256_value(second_report)
    unique_output_paths = len(all_paths) == len(set(all_paths))

    criteria = {
        "all_targets_have_one_result_per_run": first_parity and second_parity,
        "target_crosswalk_parity": crosswalk_parity,
        "all_targets_resolve_classify_and_generate": passed_count
        == expected_target_count,
        "all_targets_are_deterministic": (
            deterministic_count == expected_target_count and reports_identical
        ),
        "all_nesting_relationships_preserved_as_lists": (
            nesting_parity_count == expected_target_count
        ),
        "all_output_paths_are_unique": unique_output_paths,
        "zero_target_only_production_patches": target_only_patch_count == 0,
    }
    gate_passed = all(criteria.values())
    seed = {
        "manifest_sha256": manifest_sha,
        "first_run_id": first_report.get("run_id"),
        "second_run_id": second_report.get("run_id"),
        "crosswalk_sha256": _sha256_value(crosswalk),
        "criteria": criteria,
        "targets": outcomes,
    }
    return {
        "schema_version": 1,
        "batch_id": "WA-PB01",
        "wave": wave,
        "manifest_name": manifest.name,
        "manifest_sha256": manifest_sha,
        "crosswalk_sha256": _sha256_value(crosswalk),
        "run_asof": first_report.get("run_asof"),
        "evaluation_id": _sha256_value(seed)[:20],
        "upstream": {
            "repository": upstream_repository,
            "revision": upstream_revision,
        },
        "first_run_id": first_report.get("run_id"),
        "second_run_id": second_report.get("run_id"),
        "summary": {
            "target_count": expected_target_count,
            "passed_count": passed_count,
            "deterministic_count": deterministic_count,
            "nesting_parity_count": nesting_parity_count,
            "reports_identical": reports_identical,
            "unique_output_paths": unique_output_paths,
            "target_only_patch_count": target_only_patch_count,
            "gate_passed": gate_passed,
        },
        "criteria": criteria,
        "targets": outcomes,
    }


def run_production_wave_acceptance(
    *,
    manifest_path: str | Path,
    first_report_path: str | Path,
    second_report_path: str | Path,
    crosswalk_path: str | Path,
    result_path: str | Path,
    upstream_repository: str,
    upstream_revision: str,
    expected_target_count: int = 20,
    target_only_patch_count: int = 0,
) -> dict[str, Any]:
    report = evaluate_production_wave(
        load_manifest(manifest_path),
        load_result_report(first_report_path),
        load_result_report(second_report_path),
        load_crosswalk(crosswalk_path),
        upstream_repository=upstream_repository,
        upstream_revision=upstream_revision,
        expected_target_count=expected_target_count,
        target_only_patch_count=target_only_patch_count,
    )
    output = Path(result_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
