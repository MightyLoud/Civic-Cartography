from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import yaml


SUPPORTED_CLASSIFICATIONS = frozenset(
    {
        "government",
        "legislature",
        "school_system",
        "executive",
        "transit_authority",
        "utility_commission",
        "judicial",
        "prosecutorial",
        "advisory_board",
        "special_purpose_district",
    }
)
SUPPORTED_CATEGORIES = frozenset(
    {"regression_fixture", "new_known_archetype", "discovery", "production"}
)
SUPPORTED_SELECTOR_TYPES = frozenset({"ocdid", "explicit_lookup", "alias_group"})
SUPPORTED_MATCH_STATUSES = frozenset(
    {
        "resolved",
        "matched",
        "unresolved",
        "alias_group_pending",
        "not_found",
        "ambiguous",
    }
)
SUPPORTED_CLASSIFICATION_STATUSES = frozenset(
    {"not_evaluated", "matched", "mismatch", "not_applicable"}
)
SUPPORTED_GENERATION_STATUSES = frozenset(
    {"not_run", "generated", "partial", "failed", "skipped"}
)
SUPPORTED_RESOLUTION_POLICIES = frozenset({"override_or_exception"})
TARGET_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
STATE_PATTERN = re.compile(r"^[a-z]{2}$")
US_ADMIN1_TYPES = ("state", "district", "territory")
CENSUS_PLACE_GEOID_PATTERN = re.compile(r"^[0-9]{7}$")
CENSUS_COUNTY_GEOID_PATTERN = re.compile(r"^[0-9]{5}$")
WAVE_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")


class ManifestError(ValueError):
    """Raised when a target manifest or execution result is invalid."""


@dataclass(frozen=True)
class Target:
    target_id: str
    jurisdiction_name: str
    state: str
    selector: dict[str, Any]
    expected_archetype: str
    expected_classification: str
    category: str
    census_geoid: str | None = None
    wave: str | None = None


@dataclass(frozen=True)
class TargetManifest:
    version: int
    name: str
    description: str | None
    run_asof: str | None
    targets: tuple[Target, ...]
    state: str | None = None
    source_manifest: str | None = None
    selection_crosswalk: str | None = None


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{location} must be a mapping")
    return dict(value)


def _require_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{location} must be a non-empty string")
    return value.strip()


def _require_string_list(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ManifestError(f"{location} must be a non-empty list")
    return [
        _require_nonempty_string(item, f"{location}[{index}]")
        for index, item in enumerate(value)
    ]


def normalize_run_asof(value: str) -> str:
    raw = _require_nonempty_string(value, "run_asof")
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ManifestError("run_asof must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ManifestError("run_asof must include a timezone")
    return (
        parsed.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _normalize_ocdid(value: Any, state: str, location: str) -> str:
    ocdid = _require_nonempty_string(value, location).rstrip("/")
    prefix = "ocd-division/country:us/"
    if not ocdid.startswith(prefix):
        raise ManifestError(f"{location} must be a U.S. ocd-division ID")
    admin1_markers = tuple(f"/{kind}:{state}/" for kind in US_ADMIN1_TYPES)
    if not any(marker in f"/{ocdid}/" for marker in admin1_markers):
        supported = ", ".join(f"{kind}:{state}" for kind in US_ADMIN1_TYPES)
        raise ManifestError(
            f"{location} must contain one of the supported U.S. admin-1 "
            f"markers: {supported}"
        )
    return ocdid


def _validate_selector(
    raw_selector: Any, state: str, location: str
) -> dict[str, Any]:
    selector = _require_mapping(raw_selector, location)
    selector_type = _require_nonempty_string(
        selector.get("type"), f"{location}.type"
    )
    if selector_type not in SUPPORTED_SELECTOR_TYPES:
        raise ManifestError(
            f"{location}.type must be one of {sorted(SUPPORTED_SELECTOR_TYPES)}"
        )

    if selector_type == "ocdid":
        allowed = {"type", "value"}
        extra = set(selector) - allowed
        if extra:
            raise ManifestError(f"{location} has unsupported keys: {sorted(extra)}")
        return {
            "type": "ocdid",
            "value": _normalize_ocdid(
                selector.get("value"), state, f"{location}.value"
            ),
        }

    if selector_type == "explicit_lookup":
        allowed = {"type", "name", "resolution_policy"}
        extra = set(selector) - allowed
        if extra:
            raise ManifestError(f"{location} has unsupported keys: {sorted(extra)}")
        policy = _require_nonempty_string(
            selector.get("resolution_policy"), f"{location}.resolution_policy"
        )
        if policy not in SUPPORTED_RESOLUTION_POLICIES:
            raise ManifestError(
                f"{location}.resolution_policy must be one of "
                f"{sorted(SUPPORTED_RESOLUTION_POLICIES)}"
            )
        return {
            "type": "explicit_lookup",
            "name": _require_nonempty_string(
                selector.get("name"), f"{location}.name"
            ),
            "resolution_policy": policy,
        }

    allowed = {"type", "members", "canonical_rule"}
    extra = set(selector) - allowed
    if extra:
        raise ManifestError(f"{location} has unsupported keys: {sorted(extra)}")
    members = _require_string_list(selector.get("members"), f"{location}.members")
    normalized_members = [
        _normalize_ocdid(member, state, f"{location}.members[{index}]")
        for index, member in enumerate(members)
    ]
    if len(normalized_members) < 2:
        raise ManifestError(f"{location}.members must contain at least two OCD IDs")
    if len(set(normalized_members)) != len(normalized_members):
        raise ManifestError(f"{location}.members must not contain duplicates")
    return {
        "type": "alias_group",
        "members": normalized_members,
        "canonical_rule": _require_nonempty_string(
            selector.get("canonical_rule"), f"{location}.canonical_rule"
        ),
    }


def _normalize_relative_path(value: Any, location: str) -> str:
    raw = _require_nonempty_string(value, location)
    candidate = PurePosixPath(raw.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ManifestError(f"{location} must be a contained relative path")
    normalized = candidate.as_posix()
    if normalized in {"", "."}:
        raise ManifestError(f"{location} must identify a file")
    return normalized


def _selector_geography_type(selector: Mapping[str, Any]) -> str | None:
    selector_type = selector.get("type")
    values: list[str]
    if selector_type == "ocdid":
        value = selector.get("value")
        values = [value] if isinstance(value, str) else []
    elif selector_type == "alias_group":
        raw_members = selector.get("members")
        values = [item for item in raw_members or [] if isinstance(item, str)]
    else:
        # Existing explicit-lookup production targets predate geography typing and
        # remain place-compatible until an exact OCD ID resolves them.
        return "place"

    kinds: set[str] = set()
    for value in values:
        if "/place:" in value:
            kinds.add("place")
        elif "/county:" in value:
            kinds.add("county")
        else:
            kinds.add("other")
    if len(kinds) != 1:
        return None
    kind = next(iter(kinds))
    return kind if kind in {"place", "county"} else None


def _validate_production_geoid(
    census_geoid: str, selector: Mapping[str, Any], location: str
) -> None:
    geography_type = _selector_geography_type(selector)
    if geography_type == "place":
        if not CENSUS_PLACE_GEOID_PATTERN.fullmatch(census_geoid):
            raise ManifestError(
                f"{location}.census_geoid must be a seven-digit Census place GEOID "
                "for a place selector"
            )
        return
    if geography_type == "county":
        if not CENSUS_COUNTY_GEOID_PATTERN.fullmatch(census_geoid):
            raise ManifestError(
                f"{location}.census_geoid must be a five-digit Census county GEOID "
                "for a county selector"
            )
        return
    raise ManifestError(
        f"{location}.selector must resolve to a single supported production "
        "geography type (place or county)"
    )


def _validate_target(raw_target: Any, index: int) -> Target:
    location = f"targets[{index}]"
    target = _require_mapping(raw_target, location)
    allowed = {
        "target_id",
        "jurisdiction_name",
        "state",
        "selector",
        "expected_archetype",
        "expected_classification",
        "category",
        "census_geoid",
        "wave",
    }
    extra = set(target) - allowed
    if extra:
        raise ManifestError(f"{location} has unsupported keys: {sorted(extra)}")

    target_id = _require_nonempty_string(
        target.get("target_id"), f"{location}.target_id"
    )
    if not TARGET_ID_PATTERN.fullmatch(target_id):
        raise ManifestError(
            f"{location}.target_id must contain only uppercase letters, "
            "numbers, underscores, or hyphens"
        )

    state = _require_nonempty_string(target.get("state"), f"{location}.state").lower()
    if not STATE_PATTERN.fullmatch(state):
        raise ManifestError(f"{location}.state must be a two-letter code")

    selector = _validate_selector(target.get("selector"), state, f"{location}.selector")

    expected_classification = _require_nonempty_string(
        target.get("expected_classification"),
        f"{location}.expected_classification",
    )
    if expected_classification not in SUPPORTED_CLASSIFICATIONS:
        raise ManifestError(
            f"{location}.expected_classification must be one of "
            f"{sorted(SUPPORTED_CLASSIFICATIONS)}"
        )

    category = _require_nonempty_string(
        target.get("category"), f"{location}.category"
    )
    if category not in SUPPORTED_CATEGORIES:
        raise ManifestError(
            f"{location}.category must be one of {sorted(SUPPORTED_CATEGORIES)}"
        )

    raw_census_geoid = target.get("census_geoid")
    raw_wave = target.get("wave")
    census_geoid = None
    wave = None
    if category == "production":
        census_geoid = _require_nonempty_string(
            raw_census_geoid, f"{location}.census_geoid"
        )
        _validate_production_geoid(census_geoid, selector, location)
        wave = _require_nonempty_string(raw_wave, f"{location}.wave")
        if not WAVE_PATTERN.fullmatch(wave):
            raise ManifestError(
                f"{location}.wave must contain uppercase letters, numbers, and hyphens"
            )
    elif raw_census_geoid is not None or raw_wave is not None:
        raise ManifestError(
            f"{location}.census_geoid and wave are reserved for production targets"
        )

    return Target(
        target_id=target_id,
        jurisdiction_name=_require_nonempty_string(
            target.get("jurisdiction_name"), f"{location}.jurisdiction_name"
        ),
        state=state,
        selector=selector,
        expected_archetype=_require_nonempty_string(
            target.get("expected_archetype"),
            f"{location}.expected_archetype",
        ),
        expected_classification=expected_classification,
        category=category,
        census_geoid=census_geoid,
        wave=wave,
    )


def load_manifest(path: str | Path) -> TargetManifest:
    manifest_path = Path(path)
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"Manifest not found: {manifest_path}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"Manifest YAML is invalid: {manifest_path}") from exc

    root = _require_mapping(raw, "manifest")
    allowed = {
        "version",
        "name",
        "description",
        "run_asof",
        "state",
        "source_manifest",
        "selection_crosswalk",
        "targets",
    }
    extra = set(root) - allowed
    if extra:
        raise ManifestError(f"manifest has unsupported keys: {sorted(extra)}")

    version = root.get("version")
    if version != 1:
        raise ManifestError("manifest.version must be 1")

    raw_targets = root.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ManifestError("manifest.targets must be a non-empty list")

    targets = tuple(
        _validate_target(item, index) for index, item in enumerate(raw_targets)
    )
    target_ids = [target.target_id for target in targets]
    duplicates = sorted(
        target_id
        for target_id, count in Counter(target_ids).items()
        if count > 1
    )
    if duplicates:
        raise ManifestError(f"target IDs must be unique: {duplicates}")

    raw_asof = root.get("run_asof")
    run_asof = normalize_run_asof(raw_asof) if raw_asof is not None else None
    description = root.get("description")
    if description is not None:
        description = _require_nonempty_string(description, "manifest.description")

    raw_state = root.get("state")
    state = None
    if raw_state is not None:
        state = _require_nonempty_string(raw_state, "manifest.state").lower()
        if not STATE_PATTERN.fullmatch(state):
            raise ManifestError("manifest.state must be a two-letter code")
        if {target.state for target in targets} != {state}:
            raise ManifestError("manifest.state must match every target state")

    raw_source_manifest = root.get("source_manifest")
    raw_selection_crosswalk = root.get("selection_crosswalk")
    source_manifest = (
        _normalize_relative_path(raw_source_manifest, "manifest.source_manifest")
        if raw_source_manifest is not None
        else None
    )
    selection_crosswalk = (
        _normalize_relative_path(
            raw_selection_crosswalk, "manifest.selection_crosswalk"
        )
        if raw_selection_crosswalk is not None
        else None
    )
    if any(target.category == "production" for target in targets):
        missing = [
            name
            for name, value in (
                ("state", state),
                ("source_manifest", source_manifest),
                ("selection_crosswalk", selection_crosswalk),
            )
            if value is None
        ]
        if missing:
            raise ManifestError(
                f"production manifests require root metadata: {missing}"
            )

    return TargetManifest(
        version=1,
        name=_require_nonempty_string(root.get("name"), "manifest.name"),
        description=description,
        run_asof=run_asof,
        targets=targets,
        state=state,
        source_manifest=source_manifest,
        selection_crosswalk=selection_crosswalk,
    )


def manifest_to_dict(manifest: TargetManifest) -> dict[str, Any]:
    root: dict[str, Any] = {
        "version": manifest.version,
        "name": manifest.name,
        "description": manifest.description,
        "run_asof": manifest.run_asof,
        "targets": [],
    }
    if manifest.state is not None:
        root["state"] = manifest.state
    if manifest.source_manifest is not None:
        root["source_manifest"] = manifest.source_manifest
    if manifest.selection_crosswalk is not None:
        root["selection_crosswalk"] = manifest.selection_crosswalk

    targets: list[dict[str, Any]] = []
    for target in manifest.targets:
        row = {
            "target_id": target.target_id,
            "jurisdiction_name": target.jurisdiction_name,
            "state": target.state,
            "selector": target.selector,
            "expected_archetype": target.expected_archetype,
            "expected_classification": target.expected_classification,
            "category": target.category,
        }
        if target.census_geoid is not None:
            row["census_geoid"] = target.census_geoid
        if target.wave is not None:
            row["wave"] = target.wave
        targets.append(row)
    root["targets"] = targets
    return root


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _baseline_result(target: Target) -> dict[str, Any]:
    selector_type = target.selector["type"]
    if selector_type == "ocdid":
        resolved_ocdids = [target.selector["value"]]
        match_status = "resolved"
        exception_class = "upstream_execution_required"
        review_reason = (
            "Exact OCD ID resolved; no upstream generator execution result "
            "was supplied."
        )
    elif selector_type == "explicit_lookup":
        resolved_ocdids = []
        match_status = "unresolved"
        exception_class = "explicit_lookup_required"
        review_reason = (
            "Named target requires a maintained override or authoritative "
            "lookup result."
        )
    else:
        resolved_ocdids = list(target.selector["members"])
        match_status = "alias_group_pending"
        exception_class = "alias_resolution_required"
        review_reason = (
            "Alias members are explicit, but the canonical jurisdiction rule "
            "has not been evaluated."
        )

    result = {
        "target_id": target.target_id,
        "jurisdiction_name": target.jurisdiction_name,
        "state": target.state,
        "category": target.category,
        "expected_archetype": target.expected_archetype,
        "requested_selector": target.selector,
        "resolved_ocdids": resolved_ocdids,
        "match_status": match_status,
        "expected_classification": target.expected_classification,
        "inferred_classification": None,
        "classification_status": "not_evaluated",
        "generation_status": "not_run",
        "division_paths": [],
        "jurisdiction_paths": [],
        "exception_class": exception_class,
        "review_reason": review_reason,
        "human_minutes": None,
        "output_hashes": {},
    }
    if target.census_geoid is not None:
        result["census_geoid"] = target.census_geoid
    if target.wave is not None:
        result["wave"] = target.wave
    return result


OVERLAY_FIELDS = frozenset(
    {
        "resolved_ocdids",
        "match_status",
        "inferred_classification",
        "classification_status",
        "generation_status",
        "division_paths",
        "jurisdiction_paths",
        "exception_class",
        "review_reason",
        "human_minutes",
    }
)


def load_execution_results(
    path: str | Path | None, target_ids: set[str]
) -> tuple[dict[str, dict[str, Any]], str | None]:
    if path is None:
        return {}, None
    result_path = Path(path)
    try:
        raw = json.loads(result_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"Execution results not found: {result_path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"Execution results JSON is invalid: {result_path}"
        ) from exc

    root = _require_mapping(raw, "execution_results")
    if set(root) != {"version", "results"}:
        raise ManifestError(
            "execution_results must contain exactly 'version' and 'results'"
        )
    if root["version"] != 1:
        raise ManifestError("execution_results.version must be 1")
    results = _require_mapping(root["results"], "execution_results.results")
    unknown = sorted(set(results) - target_ids)
    if unknown:
        raise ManifestError(f"execution results contain unknown targets: {unknown}")

    normalized: dict[str, dict[str, Any]] = {}
    for target_id, raw_overlay in results.items():
        overlay = _require_mapping(
            raw_overlay, f"execution_results.results.{target_id}"
        )
        extra = set(overlay) - OVERLAY_FIELDS
        if extra:
            raise ManifestError(
                f"execution_results.results.{target_id} has unsupported keys: "
                f"{sorted(extra)}"
            )
        normalized[target_id] = _validate_overlay(target_id, overlay)
    return normalized, _sha256_value(root)


def _validate_optional_string(value: Any, location: str) -> str | None:
    if value is None:
        return None
    return _require_nonempty_string(value, location)


def _validate_overlay(target_id: str, overlay: Mapping[str, Any]) -> dict[str, Any]:
    location = f"execution_results.results.{target_id}"
    result = dict(overlay)

    if "resolved_ocdids" in result:
        value = result["resolved_ocdids"]
        if not isinstance(value, list):
            raise ManifestError(f"{location}.resolved_ocdids must be a list")
        result["resolved_ocdids"] = [
            _require_nonempty_string(item, f"{location}.resolved_ocdids[{index}]")
            for index, item in enumerate(value)
        ]

    enum_fields = {
        "match_status": SUPPORTED_MATCH_STATUSES,
        "classification_status": SUPPORTED_CLASSIFICATION_STATUSES,
        "generation_status": SUPPORTED_GENERATION_STATUSES,
    }
    for field, allowed in enum_fields.items():
        if field in result:
            value = _require_nonempty_string(result[field], f"{location}.{field}")
            if value not in allowed:
                raise ManifestError(
                    f"{location}.{field} must be one of {sorted(allowed)}"
                )
            result[field] = value

    if "inferred_classification" in result:
        value = _validate_optional_string(
            result["inferred_classification"],
            f"{location}.inferred_classification",
        )
        if value is not None and value not in SUPPORTED_CLASSIFICATIONS:
            raise ManifestError(
                f"{location}.inferred_classification must be one of "
                f"{sorted(SUPPORTED_CLASSIFICATIONS)}"
            )
        result["inferred_classification"] = value

    for field in ("division_paths", "jurisdiction_paths"):
        if field in result:
            value = result[field]
            if not isinstance(value, list):
                raise ManifestError(f"{location}.{field} must be a list")
            result[field] = [
                _require_nonempty_string(item, f"{location}.{field}[{index}]")
                for index, item in enumerate(value)
            ]

    for field in ("exception_class", "review_reason"):
        if field in result:
            result[field] = _validate_optional_string(
                result[field], f"{location}.{field}"
            )

    if "human_minutes" in result:
        value = result["human_minutes"]
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
        ):
            raise ManifestError(
                f"{location}.human_minutes must be a non-negative number or null"
            )
    return result


def _normalized_relative_path(value: str) -> str:
    return _normalize_relative_path(value, "artifact path")


def _hash_artifacts(result: dict[str, Any], artifact_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    paths = list(result["division_paths"]) + list(result["jurisdiction_paths"])
    for raw_path in paths:
        normalized = _normalized_relative_path(raw_path)
        file_path = artifact_root / normalized
        if not file_path.is_file():
            raise ManifestError(
                f"artifact path for {result['target_id']} does not exist: {normalized}"
            )
        hashes[normalized] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return dict(sorted(hashes.items()))


def _validate_result_consistency(result: Mapping[str, Any]) -> None:
    target_id = result["target_id"]
    if result["match_status"] == "matched" and not result["resolved_ocdids"]:
        raise ManifestError(f"{target_id}: matched targets require resolved_ocdids")
    if (
        result["classification_status"] == "matched"
        and result["inferred_classification"] != result["expected_classification"]
    ):
        raise ManifestError(
            f"{target_id}: classification_status=matched requires expected and "
            "inferred classifications to agree"
        )
    if (
        result["classification_status"] == "mismatch"
        and result["inferred_classification"] == result["expected_classification"]
    ):
        raise ManifestError(
            f"{target_id}: classification_status=mismatch requires different "
            "expected and inferred classifications"
        )
    if result["generation_status"] == "generated" and not (
        result["division_paths"] or result["jurisdiction_paths"]
    ):
        raise ManifestError(
            f"{target_id}: generated targets require at least one artifact path"
        )
    if (
        result["generation_status"] != "generated"
        and result["exception_class"] is None
        and not result["review_reason"]
    ):
        raise ManifestError(
            f"{target_id}: non-generated targets require an exception class or "
            "review reason"
        )


def build_report(
    manifest: TargetManifest,
    run_asof: str | None = None,
    execution_results: Mapping[str, Mapping[str, Any]] | None = None,
    execution_results_sha256: str | None = None,
    artifact_root: str | Path = ".",
) -> dict[str, Any]:
    resolved_asof = normalize_run_asof(run_asof or manifest.run_asof or "")
    overlays = execution_results or {}
    root = Path(artifact_root)

    results: list[dict[str, Any]] = []
    for target in manifest.targets:
        result = _baseline_result(target)
        overlay = overlays.get(target.target_id)
        if overlay:
            result.update(dict(overlay))
        result["output_hashes"] = _hash_artifacts(result, root)
        _validate_result_consistency(result)
        results.append(result)

    manifest_dict = manifest_to_dict(manifest)
    manifest_sha256 = _sha256_value(manifest_dict)
    selector_counts = Counter(target.selector["type"] for target in manifest.targets)
    generation_counts = Counter(result["generation_status"] for result in results)
    exception_count = sum(
        1 for result in results if result["exception_class"] is not None
    )
    summary = {
        "target_count": len(results),
        "state_count": len({target.state for target in manifest.targets}),
        "fixture_count": sum(
            target.category == "regression_fixture" for target in manifest.targets
        ),
        "discovery_count": sum(
            target.category == "discovery" for target in manifest.targets
        ),
        "selector_counts": dict(sorted(selector_counts.items())),
        "generation_counts": dict(sorted(generation_counts.items())),
        "exception_count": exception_count,
    }
    production_count = sum(
        target.category == "production" for target in manifest.targets
    )
    if production_count:
        summary["production_count"] = production_count
    run_seed = {
        "manifest_sha256": manifest_sha256,
        "execution_results_sha256": execution_results_sha256,
        "run_asof": resolved_asof,
        "results": results,
    }
    return {
        "schema_version": 1,
        "manifest_name": manifest.name,
        "manifest_sha256": manifest_sha256,
        "execution_results_sha256": execution_results_sha256,
        "run_asof": resolved_asof,
        "run_id": _sha256_value(run_seed)[:20],
        "states": sorted({target.state for target in manifest.targets}),
        "summary": summary,
        "results": results,
    }


def write_report(report: Mapping[str, Any], path: str | Path) -> None:
    result_path = Path(path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_manifest(
    manifest_path: str | Path,
    result_path: str | Path,
    run_asof: str | None = None,
    execution_results_path: str | Path | None = None,
    artifact_root: str | Path = ".",
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    overlays, overlay_sha = load_execution_results(
        execution_results_path,
        {target.target_id for target in manifest.targets},
    )
    report = build_report(
        manifest,
        run_asof=run_asof,
        execution_results=overlays,
        execution_results_sha256=overlay_sha,
        artifact_root=artifact_root,
    )
    write_report(report, result_path)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a deliberate jurisdiction target manifest and emit one "
            "deterministic result record per target."
        )
    )
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--result-path", required=True)
    parser.add_argument(
        "--run-asof",
        help=(
            "Timezone-aware ISO-8601 run timestamp. Required unless the manifest "
            "declares run_asof."
        ),
    )
    parser.add_argument(
        "--execution-results",
        help="Optional JSON results supplied by an upstream generator adapter.",
    )
    parser.add_argument(
        "--artifact-root",
        default=".",
        help=(
            "Base directory for generated artifact paths "
            "(default: current directory)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_manifest(
            manifest_path=args.target_manifest,
            result_path=args.result_path,
            run_asof=args.run_asof,
            execution_results_path=args.execution_results,
            artifact_root=args.artifact_root,
        )
    except ManifestError as exc:
        print(f"target-manifest error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Wrote {report['summary']['target_count']} target results "
        f"to {args.result_path} (run_id={report['run_id']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
