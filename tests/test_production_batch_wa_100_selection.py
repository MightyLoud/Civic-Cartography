from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "production_batch_wa_100.yml"
SOURCE_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-100"
    / "selection"
    / "source-selection-manifest.json"
)
CROSSWALK_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-100"
    / "selection"
    / "selection-crosswalk.json"
)


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def _source() -> dict:
    return json.loads(SOURCE_PATH.read_text(encoding="utf-8"))


def _crosswalk() -> dict:
    return json.loads(CROSSWALK_PATH.read_text(encoding="utf-8"))


def test_source_counts_reconcile_to_the_active_municipal_inventory() -> None:
    counts = _source()["counts"]
    assert counts["active_incorporated_municipalities"] == 281
    assert counts["tracker_rows"] == 281
    assert counts["tracker_complete_exclusions"] == 116
    assert counts["eligible_pool"] == 165
    assert counts["selected_targets"] == 100
    assert counts["replacement_queue"] == 10
    assert counts["eligible_not_selected"] == 55
    assert (
        counts["tracker_complete_exclusions"]
        + counts["selected_targets"]
        + counts["replacement_queue"]
        + counts["eligible_not_selected"]
        == counts["active_incorporated_municipalities"]
    )
    assert counts["unresolved_tracker_rows"] == 0
    assert counts["unresolved_maintained_ocdids"] == 0


def test_manifest_has_exact_deterministic_target_ids_and_waves() -> None:
    targets = _manifest()["targets"]
    assert len(targets) == 100
    assert [row["target_id"] for row in targets] == [
        f"WA-PB01-{number:03d}" for number in range(1, 101)
    ]
    assert [row["census_geoid"] for row in targets] == sorted(
        row["census_geoid"] for row in targets
    )
    assert [row["wave"] for row in targets] == [
        f"WA-PB01-{'ABCDE'[(number - 1) // 20]}" for number in range(1, 101)
    ]
    assert {row["expected_archetype"] for row in targets} == {"AR-001"}
    assert {row["expected_classification"] for row in targets} == {"government"}
    assert {row["selector"]["type"] for row in targets} == {"ocdid"}
    assert len({row["selector"]["value"] for row in targets}) == 100


def test_crosswalk_covers_targets_and_replacements_once() -> None:
    rows = _crosswalk()["candidates"]
    assert len(rows) == 110
    assert len({row["census_geoid"] for row in rows}) == 110
    assert len({row["maintained_ocdid"] for row in rows}) == 110
    assert [row["census_geoid"] for row in rows] == sorted(
        row["census_geoid"] for row in rows
    )
    assert {
        disposition: sum(row["disposition"] == disposition for row in rows)
        for disposition in {"target", "replacement_queue"}
    } == {
        "target": 100,
        "replacement_queue": 10,
    }


def test_manifest_and_target_crosswalk_match_exactly() -> None:
    manifest_targets = _manifest()["targets"]
    crosswalk_targets = [
        row for row in _crosswalk()["candidates"] if row["disposition"] == "target"
    ]
    assert [
        (
            row["target_id"],
            row["census_geoid"],
            row["selector"]["value"],
            row["wave"],
        )
        for row in manifest_targets
    ] == [
        (
            row["target_id"],
            row["census_geoid"],
            row["maintained_ocdid"],
            row["wave"],
        )
        for row in crosswalk_targets
    ]


def test_nesting_relationships_remain_lists() -> None:
    targets = {
        row["display_name"]: row
        for row in _crosswalk()["candidates"]
        if row["disposition"] == "target"
    }
    for row in targets.values():
        nesting = row["nesting"]
        assert isinstance(nesting["county_fips"], list) and nesting["county_fips"]
        assert isinstance(nesting["county_names"], list) and nesting["county_names"]
        assert isinstance(nesting["sldu_fips"], list) and nesting["sldu_fips"]
        assert isinstance(nesting["sldl_fips"], list) and nesting["sldl_fips"]

    assert targets["Milton"]["nesting"]["county_fips"] == ["033", "053"]
    assert targets["Pacific"]["nesting"]["county_fips"] == ["033", "053"]
    assert targets["Richland"]["nesting"]["sldu_fips"] == ["008", "016"]
    assert targets["Richland"]["nesting"]["sldl_fips"] == ["008", "016"]


def test_replacement_queue_follows_the_targets_without_overlap() -> None:
    rows = _crosswalk()["candidates"]
    targets = [row for row in rows if row["disposition"] == "target"]
    replacements = [
        row for row in rows if row["disposition"] == "replacement_queue"
    ]
    assert [row["replacement_id"] for row in replacements] == [
        f"WA-PB01-R{number:02d}" for number in range(1, 11)
    ]
    assert targets[-1]["census_geoid"] < replacements[0]["census_geoid"]
    assert not (
        {row["census_geoid"] for row in targets}
        & {row["census_geoid"] for row in replacements}
    )
