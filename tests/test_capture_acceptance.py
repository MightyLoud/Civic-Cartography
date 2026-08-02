from __future__ import annotations

from copy import deepcopy

from scripts.normalize_capture_acceptance import normalize_capture_semantics


PIERCE = "ocd-division/country:us/state:wa/county:pierce"
DENVER_PLACE = "ocd-division/country:us/state:co/place:denver"
DENVER_COUNTY = "ocd-division/country:us/state:co/county:denver"


def _target(target_id: str, selector: dict[str, object]) -> dict[str, object]:
    return {
        "target_id": target_id,
        "jurisdiction_name": target_id,
        "selector": selector,
    }


def _overlay(
    *,
    resolved_ocdids: list[str],
    division_paths: list[str],
    jurisdiction_paths: list[str],
) -> dict[str, object]:
    return {
        "resolved_ocdids": resolved_ocdids,
        "match_status": "matched",
        "inferred_classification": "government",
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
