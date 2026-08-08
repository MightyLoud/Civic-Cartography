from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping


REGISTER_FIELDS = (
    "target_id",
    "jurisdiction_name",
    "state",
    "evaluation_id",
    "raw_exists",
    "normalized_exists",
    "identifier_join_ok",
    "qa_ok",
    "parity_ok",
    "source_provenance_ok",
    "complete_ok",
    "confidence",
    "failed_gates",
    "source_manifest_sha256",
    "manifest_sha256",
    "first_run_id",
    "second_run_id",
    "run_asof",
    "evidence_ref",
)


class CompletionRegisterError(ValueError):
    """Raised when completion-manifest evidence cannot be projected safely."""


def load_completion_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompletionRegisterError(
            f"completion manifest not found: {manifest_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CompletionRegisterError(
            f"completion manifest is invalid JSON: {manifest_path}"
        ) from exc
    if not isinstance(raw, dict):
        raise CompletionRegisterError("completion manifest must be a mapping")
    return raw


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompletionRegisterError(f"{location} must be a non-empty string")
    return value.strip()


def _bool_text(value: Any, location: str) -> str:
    if not isinstance(value, bool):
        raise CompletionRegisterError(f"{location} must be boolean")
    return "TRUE" if value else "FALSE"


def completion_register_rows(
    completion_manifest: Mapping[str, Any], *, evidence_ref: str
) -> list[dict[str, str]]:
    if completion_manifest.get("schema_version") != 1:
        raise CompletionRegisterError("completion manifest schema_version must be 1")
    evaluation_id = _require_string(
        completion_manifest.get("evaluation_id"), "evaluation_id"
    )
    source_manifest_sha256 = _require_string(
        completion_manifest.get("source_manifest_sha256"), "source_manifest_sha256"
    )
    manifest_sha256 = _require_string(
        completion_manifest.get("manifest_sha256"), "manifest_sha256"
    )
    first_run_id = _require_string(
        completion_manifest.get("first_run_id"), "first_run_id"
    )
    second_run_id = _require_string(
        completion_manifest.get("second_run_id"), "second_run_id"
    )
    run_asof = _require_string(completion_manifest.get("run_asof"), "run_asof")
    evidence_ref = _require_string(evidence_ref, "evidence_ref")

    raw_targets = completion_manifest.get("targets")
    if not isinstance(raw_targets, list):
        raise CompletionRegisterError("completion manifest targets must be a list")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw_target in enumerate(raw_targets):
        if not isinstance(raw_target, dict):
            raise CompletionRegisterError(f"targets[{index}] must be a mapping")
        target_id = _require_string(raw_target.get("target_id"), f"targets[{index}].target_id")
        if target_id in seen:
            raise CompletionRegisterError(f"duplicate completion target: {target_id}")
        seen.add(target_id)
        failed_gates = raw_target.get("failed_gates")
        if not isinstance(failed_gates, list) or any(
            not isinstance(item, str) or not item for item in failed_gates
        ):
            raise CompletionRegisterError(
                f"targets[{index}].failed_gates must be a string list"
            )

        rows.append(
            {
                "target_id": target_id,
                "jurisdiction_name": _require_string(
                    raw_target.get("jurisdiction_name"),
                    f"targets[{index}].jurisdiction_name",
                ),
                "state": _require_string(
                    raw_target.get("state"), f"targets[{index}].state"
                ),
                "evaluation_id": evaluation_id,
                "raw_exists": _bool_text(
                    raw_target.get("raw_exists"), f"targets[{index}].raw_exists"
                ),
                "normalized_exists": _bool_text(
                    raw_target.get("normalized_exists"),
                    f"targets[{index}].normalized_exists",
                ),
                "identifier_join_ok": _bool_text(
                    raw_target.get("identifier_join_ok"),
                    f"targets[{index}].identifier_join_ok",
                ),
                "qa_ok": _bool_text(
                    raw_target.get("qa_ok"), f"targets[{index}].qa_ok"
                ),
                "parity_ok": _bool_text(
                    raw_target.get("parity_ok"), f"targets[{index}].parity_ok"
                ),
                "source_provenance_ok": _bool_text(
                    raw_target.get("source_provenance_ok"),
                    f"targets[{index}].source_provenance_ok",
                ),
                "complete_ok": _bool_text(
                    raw_target.get("complete_ok"), f"targets[{index}].complete_ok"
                ),
                "confidence": _require_string(
                    raw_target.get("confidence"), f"targets[{index}].confidence"
                ),
                "failed_gates": "|".join(failed_gates),
                "source_manifest_sha256": source_manifest_sha256,
                "manifest_sha256": manifest_sha256,
                "first_run_id": first_run_id,
                "second_run_id": second_run_id,
                "run_asof": run_asof,
                "evidence_ref": evidence_ref,
            }
        )
    return rows


def _load_register(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REGISTER_FIELDS:
            raise CompletionRegisterError(
                "completion register header does not match the contract"
            )
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            target_id = _require_string(row.get("target_id"), "register.target_id")
            if target_id in rows:
                raise CompletionRegisterError(
                    f"completion register contains duplicate {target_id}"
                )
            rows[target_id] = {field: row.get(field, "") for field in REGISTER_FIELDS}
        return rows


def upsert_completion_register(
    completion_manifest: Mapping[str, Any],
    *,
    register_path: str | Path,
    evidence_ref: str,
) -> list[dict[str, str]]:
    output = Path(register_path)
    existing = _load_register(output)
    for row in completion_register_rows(completion_manifest, evidence_ref=evidence_ref):
        existing[row["target_id"]] = row

    ordered = [existing[target_id] for target_id in sorted(existing)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)
    return ordered
