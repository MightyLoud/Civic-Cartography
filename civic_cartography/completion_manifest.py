from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from civic_cartography.fixture_harness import (
    DETERMINISTIC_FIELDS,
    PASSING_MATCH_STATUSES,
    load_result_report,
)
from civic_cartography.target_manifest import Target, TargetManifest, load_manifest


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CompletionManifestError(ValueError):
    """Raised when completion evidence is malformed or incomplete."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def load_source_manifest(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    try:
        raw = json.loads(source_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompletionManifestError(f"source manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CompletionManifestError(f"source manifest is invalid JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise CompletionManifestError("source manifest must be a mapping")
    return raw


def _source_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if any(key in value for key in ("sha256", "url", "repository", "path")):
            records.append(value)
        for child in value.values():
            records.extend(_source_records(child))
    elif isinstance(value, list):
        for child in value:
            records.extend(_source_records(child))
    return records


def _source_gates(source_manifest: Mapping[str, Any]) -> tuple[bool, bool]:
    records = _source_records(source_manifest)
    raw_exists = any(
        isinstance(row.get("sha256"), str)
        and SHA256_PATTERN.fullmatch(row["sha256"])
        for row in records
    )
    provenance_ok = raw_exists and any(
        any(
            isinstance(row.get(field), str) and bool(row[field].strip())
            for field in ("url", "repository", "path", "filename")
        )
        for row in records
    )
    return raw_exists, provenance_ok


def _index_results(report: Mapping[str, Any], label: str) -> dict[str, dict[str, Any]]:
    rows = report.get("results")
    if not isinstance(rows, list):
        raise CompletionManifestError(f"{label}.results must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise CompletionManifestError(f"{label}.results[{index}] must be a mapping")
        target_id = raw.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            raise CompletionManifestError(
                f"{label}.results[{index}].target_id must be a string"
            )
        if target_id in indexed:
            raise CompletionManifestError(f"{label} contains duplicate {target_id}")
        indexed[target_id] = dict(raw)
    return indexed


def _normalized_exists(result: Mapping[str, Any]) -> bool:
    division_paths = result.get("division_paths")
    jurisdiction_paths = result.get("jurisdiction_paths")
    output_hashes = result.get("output_hashes")
    if not isinstance(division_paths, list) or not division_paths:
        return False
    if not isinstance(jurisdiction_paths, list) or not jurisdiction_paths:
        return False
    if not isinstance(output_hashes, dict) or not output_hashes:
        return False
    expected = {str(path) for path in [*division_paths, *jurisdiction_paths]}
    return set(output_hashes) == expected and all(
        isinstance(digest, str) and SHA256_PATTERN.fullmatch(digest)
        for digest in output_hashes.values()
    )


def _identifier_join_ok(target: Target, result: Mapping[str, Any]) -> bool:
    resolved = result.get("resolved_ocdids")
    if not isinstance(resolved, list) or not resolved:
        return False
    selector = target.selector
    if selector["type"] == "ocdid":
        return resolved == [selector["value"]]
    if selector["type"] == "alias_group":
        return set(resolved) == set(selector["members"]) and len(resolved) == len(
            selector["members"]
        )
    return result.get("match_status") in PASSING_MATCH_STATUSES


def _qa_ok(target: Target, result: Mapping[str, Any]) -> bool:
    return (
        result.get("match_status") in PASSING_MATCH_STATUSES
        and result.get("classification_status") == "matched"
        and result.get("inferred_classification") == target.expected_classification
        and result.get("generation_status") == "generated"
        and result.get("exception_class") is None
        and result.get("review_reason") in (None, "")
        and _normalized_exists(result)
    )


def _parity_ok(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    return all(first.get(field) == second.get(field) for field in DETERMINISTIC_FIELDS)


def _target_completion(
    target: Target,
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    *,
    raw_exists: bool,
    source_provenance_ok: bool,
) -> dict[str, Any]:
    normalized_exists = _normalized_exists(first)
    identifier_join_ok = _identifier_join_ok(target, first)
    qa_ok = _qa_ok(target, first)
    parity_ok = _parity_ok(first, second)
    gates = {
        "raw_exists": raw_exists,
        "normalized_exists": normalized_exists,
        "identifier_join_ok": identifier_join_ok,
        "qa_ok": qa_ok,
        "parity_ok": parity_ok,
        "source_provenance_ok": source_provenance_ok,
    }
    complete_ok = all(gates.values())
    return {
        "target_id": target.target_id,
        "jurisdiction_name": target.jurisdiction_name,
        "state": target.state,
        "expected_archetype": target.expected_archetype,
        "expected_classification": target.expected_classification,
        "resolved_ocdids": first.get("resolved_ocdids", []),
        "division_paths": first.get("division_paths", []),
        "jurisdiction_paths": first.get("jurisdiction_paths", []),
        "output_hashes": first.get("output_hashes", {}),
        **gates,
        "complete_ok": complete_ok,
        "status": "COMPLETE" if complete_ok else "INCOMPLETE",
        "confidence": "HIGH" if complete_ok else "UNVERIFIED",
        "failed_gates": [name for name, passed in gates.items() if not passed],
    }


def evaluate_completion_manifest(
    manifest: TargetManifest,
    first_report: Mapping[str, Any],
    second_report: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    first_by_id = _index_results(first_report, "first_report")
    second_by_id = _index_results(second_report, "second_report")
    expected_ids = {target.target_id for target in manifest.targets}
    if set(first_by_id) != expected_ids or set(second_by_id) != expected_ids:
        raise CompletionManifestError("report target IDs must exactly match the manifest")
    if first_report.get("manifest_sha256") != second_report.get("manifest_sha256"):
        raise CompletionManifestError("report manifest hashes differ")
    if first_report.get("run_asof") != second_report.get("run_asof"):
        raise CompletionManifestError("report run_asof values differ")

    raw_exists, source_provenance_ok = _source_gates(source_manifest)
    targets = [
        _target_completion(
            target,
            first_by_id[target.target_id],
            second_by_id[target.target_id],
            raw_exists=raw_exists,
            source_provenance_ok=source_provenance_ok,
        )
        for target in manifest.targets
    ]
    complete_count = sum(row["complete_ok"] for row in targets)
    gate_names = (
        "raw_exists",
        "normalized_exists",
        "identifier_join_ok",
        "qa_ok",
        "parity_ok",
        "source_provenance_ok",
    )
    gate_counts = {
        gate: sum(bool(row[gate]) for row in targets) for gate in gate_names
    }
    seed = {
        "manifest_sha256": first_report.get("manifest_sha256"),
        "first_run_id": first_report.get("run_id"),
        "second_run_id": second_report.get("run_id"),
        "source_manifest_sha256": _sha256_value(source_manifest),
        "targets": targets,
    }
    return {
        "schema_version": 1,
        "contract": (
            "RAW_EXISTS -> NORMALIZED_EXISTS -> IDENTIFIER_JOIN_OK -> QA_OK -> "
            "PARITY_OK -> SOURCE_PROVENANCE_OK -> COMPLETE_OK"
        ),
        "manifest_name": manifest.name,
        "manifest_sha256": first_report.get("manifest_sha256"),
        "run_asof": first_report.get("run_asof"),
        "first_run_id": first_report.get("run_id"),
        "second_run_id": second_report.get("run_id"),
        "source_manifest_sha256": _sha256_value(source_manifest),
        "evaluation_id": _sha256_value(seed)[:20],
        "summary": {
            "target_count": len(targets),
            "complete_count": complete_count,
            "incomplete_count": len(targets) - complete_count,
            "gate_counts": gate_counts,
            "all_complete": complete_count == len(targets),
        },
        "targets": targets,
    }


def run_completion_manifest(
    *,
    manifest_path: str | Path,
    first_report_path: str | Path,
    second_report_path: str | Path,
    source_manifest_path: str | Path,
    result_path: str | Path,
) -> dict[str, Any]:
    report = evaluate_completion_manifest(
        load_manifest(manifest_path),
        load_result_report(first_report_path),
        load_result_report(second_report_path),
        load_source_manifest(source_manifest_path),
    )
    output = Path(result_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
