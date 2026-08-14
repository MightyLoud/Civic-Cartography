from __future__ import annotations

import copy

import pytest

from scripts.compare_gillespie_derivation import compare_documents


def raw_payload(confidence: float = 0.95) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "commissioner_precinct": district,
                    "source_voting_precinct_ids": [district],
                    "assignment_confidence_min": confidence,
                    "assignment_confidence_mean": confidence,
                    "official_map_sha256": "map-sha",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[district, 0], [district, 1], [district, 0]]],
                },
            }
            for district in ("1", "2", "3", "4")
        ],
    }


def test_renderer_metric_changes_are_allowed_when_stable_content_matches() -> None:
    committed = raw_payload(0.99)
    fresh = raw_payload(0.92)

    compare_documents("raw", committed, fresh, expected_metric_count=8)


def test_assignment_or_geometry_change_fails_closed() -> None:
    committed = raw_payload()
    fresh = copy.deepcopy(committed)
    fresh["features"][0]["properties"]["source_voting_precinct_ids"] = ["9"]

    with pytest.raises(SystemExit, match="stable derivation changed"):
        compare_documents("raw", committed, fresh, expected_metric_count=8)


def test_missing_renderer_metric_fails_closed() -> None:
    committed = raw_payload()
    fresh = copy.deepcopy(committed)
    del fresh["features"][0]["properties"]["assignment_confidence_mean"]

    with pytest.raises(SystemExit, match="renderer metrics"):
        compare_documents("raw", committed, fresh, expected_metric_count=8)


def test_confidence_below_controlled_floor_fails_closed() -> None:
    committed = raw_payload()
    fresh = raw_payload(0.84)

    with pytest.raises(SystemExit, match="outside"):
        compare_documents("raw", committed, fresh, expected_metric_count=8)
