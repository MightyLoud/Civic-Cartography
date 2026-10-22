from __future__ import annotations

import copy

import pytest

from scripts.compare_schleicher_derivation import compare_contracts


def contract_payload() -> dict:
    return {
        "county": "Schleicher County",
        "assignment_confidence_min": 0.87,
        "assignment_confidence_mean": 0.94,
        "assignments": [
            {
                "voting_precinct_id": str(district),
                "commissioner_precinct": str(district),
                "confidence": 0.9,
                "mean_color_distance": 10.0 + district,
                "minimum_color_separation": 5.0 + district,
            }
            for district in range(1, 5)
        ],
        "all_voting_precincts_assigned": True,
        "interdistrict_overlap_area_degrees": 0.0,
        "union_symmetric_difference_area_degrees": 0.0,
        "source_sha256": "source-sha",
    }


def test_renderer_diagnostic_changes_are_allowed_when_stable_contract_matches() -> None:
    committed = contract_payload()
    fresh = copy.deepcopy(committed)
    for assignment in fresh["assignments"]:
        assignment["mean_color_distance"] += 0.5
        assignment["minimum_color_separation"] += 0.25

    compare_contracts(committed, fresh)


def test_assignment_change_fails_closed() -> None:
    committed = contract_payload()
    fresh = copy.deepcopy(committed)
    fresh["assignments"][0]["commissioner_precinct"] = "4"

    with pytest.raises(SystemExit, match="stable derivation contract changed"):
        compare_contracts(committed, fresh)


def test_missing_renderer_diagnostic_fails_closed() -> None:
    committed = contract_payload()
    fresh = copy.deepcopy(committed)
    del fresh["assignments"][0]["mean_color_distance"]

    with pytest.raises(SystemExit, match="renderer diagnostics"):
        compare_contracts(committed, fresh)


def test_negative_renderer_diagnostic_fails_closed() -> None:
    committed = contract_payload()
    fresh = copy.deepcopy(committed)
    fresh["assignments"][0]["minimum_color_separation"] = -0.1

    with pytest.raises(SystemExit, match="nonnegative"):
        compare_contracts(committed, fresh)
