from __future__ import annotations

from pathlib import Path

from civic_cartography.canonical_aliases import load_canonical_aliases
from scripts.normalize_canonical_alias_acceptance import (
    normalize_canonical_alias_acceptance,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALIASES = load_canonical_aliases(
    PROJECT_ROOT / "data" / "canonical_alias_groups.yml"
)
PLACE = "ocd-division/country:us/state:co/place:denver"
COUNTY = "ocd-division/country:us/state:co/county:denver"
JURISDICTION = "ocd-jurisdiction/country:us/state:co/place:denver/government"


def _target() -> dict:
    return {
        "target_id": "BP25-022",
        "state": "co",
        "selector": {
            "type": "alias_group",
            "members": [PLACE, COUNTY],
            "canonical_rule": "maintained_alias",
        },
    }


def _overlay() -> dict:
    return {
        "resolved_ocdids": [COUNTY, PLACE],
        "match_status": "matched",
        "inferred_classification": "government",
        "classification_status": "matched",
        "generation_status": "partial",
        "division_paths": ["divisions/co/local/county.yaml", "divisions/co/local/place.yaml"],
        "jurisdiction_paths": ["jurisdictions/co/local/denver.yaml"],
        "exception_class": "upstream_partial_generation",
        "review_reason": "secondary member did not emit a jurisdiction",
        "human_minutes": 0.0,
    }


def _attempts() -> list[dict]:
    return [
        {
            "ocdid": PLACE,
            "status": "success",
            "division_path": "divisions/co/local/place.yaml",
            "jurisdiction_path": "jurisdictions/co/local/denver.yaml",
            "canonical_alias_id": "co-denver-consolidated-city-county",
            "canonical_alias_is_canonical": True,
            "canonical_alias_member": PLACE,
            "canonical_division_ocdid": PLACE,
            "canonical_jurisdiction_ocdid": JURISDICTION,
            "suppress_jurisdiction_generation": False,
        },
        {
            "ocdid": COUNTY,
            "status": "partial",
            "division_path": "divisions/co/local/county.yaml",
            "jurisdiction_path": None,
            "canonical_alias_id": "co-denver-consolidated-city-county",
            "canonical_alias_is_canonical": False,
            "canonical_alias_member": COUNTY,
            "canonical_division_ocdid": PLACE,
            "canonical_jurisdiction_ocdid": JURISDICTION,
            "suppress_jurisdiction_generation": True,
        },
    ]


def test_complete_alias_group_passes_with_one_shared_jurisdiction() -> None:
    execution = {"version": 1, "results": {"BP25-022": _overlay()}}
    diagnostics = {
        "version": 1,
        "targets": [
            {
                "target_id": "BP25-022",
                "attempts": _attempts(),
                "overlay": _overlay(),
            }
        ],
    }

    normalized_execution, normalized_diagnostics = (
        normalize_canonical_alias_acceptance(
            ALIASES,
            {"BP25-022": _target()},
            execution,
            diagnostics,
        )
    )

    result = normalized_execution["results"]["BP25-022"]
    detail = normalized_diagnostics["targets"][0]
    assert result["generation_status"] == "generated"
    assert result["exception_class"] is None
    assert result["review_reason"] is None
    assert detail["canonical_alias"]["invariant_errors"] == []
    assert normalized_diagnostics["canonical_alias_semantics"]["evaluated_targets"] == [
        "BP25-022"
    ]


def test_duplicate_secondary_jurisdiction_remains_noncanonical() -> None:
    attempts = _attempts()
    attempts[1]["jurisdiction_path"] = "jurisdictions/co/local/duplicate.yaml"
    overlay = _overlay()
    overlay["jurisdiction_paths"].append("jurisdictions/co/local/duplicate.yaml")
    execution = {"version": 1, "results": {"BP25-022": overlay}}
    diagnostics = {
        "version": 1,
        "targets": [
            {
                "target_id": "BP25-022",
                "attempts": attempts,
                "overlay": overlay,
            }
        ],
    }

    normalized_execution, normalized_diagnostics = (
        normalize_canonical_alias_acceptance(
            ALIASES,
            {"BP25-022": _target()},
            execution,
            diagnostics,
        )
    )

    result = normalized_execution["results"]["BP25-022"]
    errors = normalized_diagnostics["targets"][0]["canonical_alias"][
        "invariant_errors"
    ]
    assert result["exception_class"] == "upstream_alias_noncanonical"
    assert any("duplicate Jurisdiction" in error for error in errors)
