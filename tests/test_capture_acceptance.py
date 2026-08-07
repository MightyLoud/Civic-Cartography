from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts.normalize_capture_acceptance import (
    AcceptanceSemanticsError,
    MANIFEST_NAME_SOURCE,
    normalize_capture_semantics,
)


PIERCE = "ocd-division/country:us/state:wa/county:pierce"
DENVER_PLACE = "ocd-division/country:us/state:co/place:denver"
DENVER_COUNTY = "ocd-division/country:us/state:co/county:denver"
DENVER_SCHOOLS = (
    "ocd-division/country:us/state:co/county:denver/school_district:denver_1"
)


def _target(
    target_id: str,
    selector: dict[str, object],
    *,
    jurisdiction_name: str | None = None,
) -> dict[str, object]:
    return {
        "target_id": target_id,
        "jurisdiction_name": jurisdiction_name or target_id,
        "selector": selector,
    }


def _overlay(
    *,
    resolved_ocdids: list[str],
    division_paths: list[str],
    jurisdiction_paths: list[str],
    classification: str = "government",
) -> dict[str, object]:
    return {
        "resolved_ocdids": resolved_ocdids,
        "match_status": "matched",
        "inferred_classification": classification,
        "classification_status": "matched",
        "generation_status": "partial",
        "division_paths": division_paths,
        "jurisdiction_paths": jurisdiction_paths,
        "exception_class": "upstream_partial_generation",
        "review_reason": "No validation match found",
        "human_minutes": 0.0,
    }


def _diagnostic(
    target_id: str,
    attempts: list[dict[str, object]],
    overlay: dict[str, object],
) -> dict[str, object]:
    return {
        "target_id": target_id,
        "jurisdiction_name": target_id,
        "match_status": "matched",
        "resolution_reason": None,
        "attempts": attempts,
        "overlay": deepcopy(overlay),
    }


def test_partial_enrichment_does_not_negate_complete_generation() -> None:
    target_id = "BP25-009"
    overlay = _overlay(
        resolved_ocdids=[PIERCE],
        division_paths=["divisions/wa/local/pierce.yaml"],
        jurisdiction_paths=["jurisdictions/wa/local/pierce.yaml"],
    )
    attempts = [
        {
            "ocdid": PIERCE,
            "status": "partial",
            "error": "No validation match found",
            "division_path": "divisions/wa/local/pierce.yaml",
            "jurisdiction_path": "jurisdictions/wa/local/pierce.yaml",
        }
    ]

    execution, diagnostics = normalize_capture_semantics(
        {
            target_id: _target(
                target_id,
                {"type": "ocdid", "value": PIERCE},
            )
        },
        {"version": 1, "results": {target_id: overlay}},
        {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
    )

    result = execution["results"][target_id]
    detail = diagnostics["targets"][0]
    assert result["generation_status"] == "generated"
    assert result["exception_class"] is None
    assert result["review_reason"] is None
    assert detail["enrichment_status"] == "partial"
    assert detail["enrichment_reasons"] == [
        f"{PIERCE}: status=partial; error=No validation match found"
    ]


def test_noncanonical_alias_group_remains_an_explicit_failure() -> None:
    target_id = "BP25-022"
    overlay = _overlay(
        resolved_ocdids=[DENVER_PLACE, DENVER_COUNTY],
        division_paths=[
            "divisions/co/local/denver-place.yaml",
            "divisions/co/local/denver-county.yaml",
        ],
        jurisdiction_paths=[
            "jurisdictions/co/local/denver-place.yaml",
            "jurisdictions/co/local/denver-county.yaml",
        ],
    )
    attempts = [
        {
            "ocdid": DENVER_PLACE,
            "status": "success",
            "error": None,
            "division_path": "divisions/co/local/denver-place.yaml",
            "jurisdiction_path": "jurisdictions/co/local/denver-place.yaml",
        },
        {
            "ocdid": DENVER_COUNTY,
            "status": "partial",
            "error": "No validation match found",
            "division_path": "divisions/co/local/denver-county.yaml",
            "jurisdiction_path": "jurisdictions/co/local/denver-county.yaml",
        },
    ]

    execution, diagnostics = normalize_capture_semantics(
        {
            target_id: _target(
                target_id,
                {
                    "type": "alias_group",
                    "members": [DENVER_PLACE, DENVER_COUNTY],
                    "canonical_rule": "maintained_alias",
                },
            )
        },
        {"version": 1, "results": {target_id: overlay}},
        {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
    )

    result = execution["results"][target_id]
    assert result["generation_status"] == "generated"
    assert result["exception_class"] == "upstream_alias_noncanonical"
    assert "one canonical Jurisdiction" in result["review_reason"]
    assert diagnostics["targets"][0]["enrichment_status"] == "partial"


def test_failed_enrichment_remains_blocking_even_with_artifacts() -> None:
    target_id = "BP25-009"
    overlay = _overlay(
        resolved_ocdids=[PIERCE],
        division_paths=["divisions/wa/local/pierce.yaml"],
        jurisdiction_paths=["jurisdictions/wa/local/pierce.yaml"],
    )
    attempts = [
        {
            "ocdid": PIERCE,
            "status": "failed",
            "error": "unexpected generator failure",
            "division_path": "divisions/wa/local/pierce.yaml",
            "jurisdiction_path": "jurisdictions/wa/local/pierce.yaml",
        }
    ]

    execution, diagnostics = normalize_capture_semantics(
        {
            target_id: _target(
                target_id,
                {"type": "ocdid", "value": PIERCE},
            )
        },
        {"version": 1, "results": {target_id: overlay}},
        {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
    )

    result = execution["results"][target_id]
    assert result["generation_status"] == "generated"
    assert result["exception_class"] == "upstream_enrichment_failed"
    assert "unexpected generator failure" in result["review_reason"]
    assert diagnostics["targets"][0]["enrichment_status"] == "failed"


def test_missing_jurisdiction_path_remains_partial_generation() -> None:
    target_id = "BP25-009"
    overlay = _overlay(
        resolved_ocdids=[PIERCE],
        division_paths=["divisions/wa/local/pierce.yaml"],
        jurisdiction_paths=[],
    )
    attempts = [
        {
            "ocdid": PIERCE,
            "status": "partial",
            "error": "No validation match found",
            "division_path": "divisions/wa/local/pierce.yaml",
            "jurisdiction_path": None,
        }
    ]

    execution, diagnostics = normalize_capture_semantics(
        {
            target_id: _target(
                target_id,
                {"type": "ocdid", "value": PIERCE},
            )
        },
        {"version": 1, "results": {target_id: overlay}},
        {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
    )

    result = execution["results"][target_id]
    assert result["generation_status"] == "partial"
    assert result["exception_class"] == "upstream_partial_generation"
    assert diagnostics["targets"][0]["enrichment_status"] == "partial"


def test_manifest_name_normalizes_generated_jurisdiction_after_classification(
    tmp_path: Path,
) -> None:
    target_id = "MB100-030"
    division_path = "divisions/co/local/denver_1.yaml"
    jurisdiction_path = "jurisdictions/co/local/denver_1.yaml"
    artifact_root = tmp_path / "artifacts"
    jurisdiction_file = artifact_root / jurisdiction_path
    jurisdiction_file.parent.mkdir(parents=True)
    jurisdiction_file.write_text(
        yaml.safe_dump(
            {
                "id": "jur-denver-1",
                "ocdid": (
                    "ocd-jurisdiction/country:us/state:co/county:denver/"
                    "school_district:denver_1/school_system"
                ),
                "name": "denver 1 School System",
                "classification": "school_system",
                "sourcing": [
                    {
                        "field": ["ocdid", "name", "classification"],
                        "source_name": "derived_from_division",
                        "source_type": "human_researched",
                        "source_url": {"division": "https://example.test/denver_1"},
                        "source_description": "Jurisdiction derived from Division object",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    overlay = _overlay(
        resolved_ocdids=[DENVER_SCHOOLS],
        division_paths=[division_path],
        jurisdiction_paths=[jurisdiction_path],
        classification="school_system",
    )
    attempts = [
        {
            "ocdid": DENVER_SCHOOLS,
            "status": "partial",
            "error": "No validation match found",
            "division_path": division_path,
            "jurisdiction_path": jurisdiction_path,
        }
    ]

    execution, diagnostics = normalize_capture_semantics(
        {
            target_id: _target(
                target_id,
                {"type": "ocdid", "value": DENVER_SCHOOLS},
                jurisdiction_name="Denver Public Schools",
            )
        },
        {"version": 1, "results": {target_id: overlay}},
        {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
        artifact_root=artifact_root,
    )

    result = execution["results"][target_id]
    artifact = yaml.safe_load(jurisdiction_file.read_text(encoding="utf-8"))
    assert result["classification_status"] == "matched"
    assert result["generation_status"] == "generated"
    assert result["resolved_ocdids"] == [DENVER_SCHOOLS]
    assert artifact["ocdid"].endswith("/school_system")
    assert artifact["classification"] == "school_system"
    assert artifact["name"] == "Denver Public Schools"
    assert artifact["sourcing"][0]["field"] == ["ocdid", "classification"]
    assert artifact["sourcing"][-1]["field"] == ["name"]
    assert artifact["sourcing"][-1]["source_name"] == MANIFEST_NAME_SOURCE

    detail = diagnostics["targets"][0]["jurisdiction_name_normalization"]
    assert detail["expected_name"] == "Denver Public Schools"
    assert detail["changed_count"] == 1
    assert detail["paths"][0]["previous_name"] == "denver 1 School System"
    assert diagnostics["acceptance_semantics"]["jurisdiction_name_targets"] == [
        target_id
    ]


def test_manifest_name_normalization_is_idempotent(tmp_path: Path) -> None:
    target_id = "MB100-030"
    division_path = "divisions/co/local/denver_1.yaml"
    jurisdiction_path = "jurisdictions/co/local/denver_1.yaml"
    artifact_root = tmp_path / "artifacts"
    jurisdiction_file = artifact_root / jurisdiction_path
    jurisdiction_file.parent.mkdir(parents=True)
    jurisdiction_file.write_text(
        yaml.safe_dump(
            {
                "name": "Denver Public Schools",
                "classification": "school_system",
                "sourcing": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    before = jurisdiction_file.read_bytes()
    overlay = _overlay(
        resolved_ocdids=[DENVER_SCHOOLS],
        division_paths=[division_path],
        jurisdiction_paths=[jurisdiction_path],
        classification="school_system",
    )
    attempts = [
        {
            "ocdid": DENVER_SCHOOLS,
            "status": "success",
            "error": None,
            "division_path": division_path,
            "jurisdiction_path": jurisdiction_path,
        }
    ]

    _, diagnostics = normalize_capture_semantics(
        {
            target_id: _target(
                target_id,
                {"type": "ocdid", "value": DENVER_SCHOOLS},
                jurisdiction_name="Denver Public Schools",
            )
        },
        {"version": 1, "results": {target_id: overlay}},
        {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
        artifact_root=artifact_root,
    )

    assert jurisdiction_file.read_bytes() == before
    detail = diagnostics["targets"][0]["jurisdiction_name_normalization"]
    assert detail["changed_count"] == 0
    assert detail["paths"][0]["changed"] is False


def test_manifest_name_normalization_rejects_artifact_escape(tmp_path: Path) -> None:
    target_id = "MB100-030"
    overlay = _overlay(
        resolved_ocdids=[DENVER_SCHOOLS],
        division_paths=["divisions/co/local/denver_1.yaml"],
        jurisdiction_paths=["../outside.yaml"],
        classification="school_system",
    )
    attempts = [
        {
            "ocdid": DENVER_SCHOOLS,
            "status": "success",
            "error": None,
            "division_path": "divisions/co/local/denver_1.yaml",
            "jurisdiction_path": "../outside.yaml",
        }
    ]

    with pytest.raises(AcceptanceSemanticsError, match="inside artifact_root"):
        normalize_capture_semantics(
            {
                target_id: _target(
                    target_id,
                    {"type": "ocdid", "value": DENVER_SCHOOLS},
                    jurisdiction_name="Denver Public Schools",
                )
            },
            {"version": 1, "results": {target_id: overlay}},
            {"version": 1, "targets": [_diagnostic(target_id, attempts, overlay)]},
            artifact_root=tmp_path / "artifacts",
        )
