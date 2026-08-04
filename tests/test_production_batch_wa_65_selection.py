from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "fixtures" / "production_batch_wa_65.yml"
SOURCE_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-65"
    / "selection"
    / "source-selection-manifest.json"
)
CROSSWALK_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-65"
    / "selection"
    / "selection-crosswalk.json"
)
PRIOR_CROSSWALK_PATH = (
    ROOT
    / "evidence"
    / "production-batch-wa-100"
    / "selection"
    / "selection-crosswalk.json"
)
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "target-manifest.schema.json"
FIPS_PATTERN = re.compile(r"^[0-9]{3}$")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_source_counts_reconcile_to_all_active_municipalities() -> None:
    source = _json(SOURCE_PATH)
    counts = source["counts"]

    assert counts["active_incorporated_municipalities"] == 281
    assert (
        counts["completed_before_production_batch_1"]
        + counts["production_batch_1_targets"]
        + counts["production_batch_2_targets"]
        == counts["active_incorporated_municipalities"]
    )
    assert counts["production_batch_2_targets"] == 65
    assert counts["exact_maintained_ocdid_matches"] == 65
    assert [
        counts[f"wave_{letter}_targets"] for letter in "abcd"
    ] == [20, 20, 20, 5]
    assert counts["replacement_queue"] == 0
    assert counts["duplicate_target_ids"] == 0
    assert counts["duplicate_geoids"] == 0
    assert counts["duplicate_ocdids"] == 0
    assert counts["unresolved_workbook_rows"] == 0
    assert counts["unresolved_maintained_ocdids"] == 0


def test_manifest_is_frozen_schema_valid_and_deterministic() -> None:
    manifest = _manifest()
    targets = manifest["targets"]
    schema = _json(MANIFEST_SCHEMA_PATH)

    Draft202012Validator(schema).validate(manifest)
    assert len(targets) == 65
    assert manifest["source_manifest"] == (
        "evidence/production-batch-wa-65/selection/source-selection-manifest.json"
    )
    assert manifest["selection_crosswalk"] == (
        "evidence/production-batch-wa-65/selection/selection-crosswalk.json"
    )
    assert [row["target_id"] for row in targets] == [
        f"WA-PB02-{number:03d}" for number in range(1, 66)
    ]
    assert [row["census_geoid"] for row in targets] == sorted(
        row["census_geoid"] for row in targets
    )
    assert [row["wave"] for row in targets] == [
        *(["WA-PB02-A"] * 20),
        *(["WA-PB02-B"] * 20),
        *(["WA-PB02-C"] * 20),
        *(["WA-PB02-D"] * 5),
    ]
    assert targets[0]["jurisdiction_name"] == "Roslyn"
    assert targets[-1]["jurisdiction_name"] == "Zillah"
    assert {row["expected_archetype"] for row in targets} == {"AR-001"}
    assert {row["expected_classification"] for row in targets} == {"government"}
    assert len({row["selector"]["value"] for row in targets}) == 65


def test_crosswalk_matches_every_target_and_preserves_nesting_lists() -> None:
    targets = _manifest()["targets"]
    crosswalk = _json(CROSSWALK_PATH)
    candidates = crosswalk["candidates"]

    assert crosswalk["batch_id"] == "WA-PB02"
    assert crosswalk["target_count"] == 65
    assert crosswalk["replacement_count"] == 0
    assert crosswalk["record_count"] == 65
    assert len(candidates) == 65
    assert [row["sequence"] for row in candidates] == list(range(1, 66))
    assert [row["census_geoid"] for row in candidates] == sorted(
        row["census_geoid"] for row in candidates
    )
    assert len({row["target_id"] for row in candidates}) == 65
    assert len({row["census_geoid"] for row in candidates}) == 65
    assert len({row["maintained_ocdid"] for row in candidates}) == 65

    assert [
        (
            target["target_id"],
            target["jurisdiction_name"],
            target["census_geoid"],
            target["selector"]["value"],
            target["expected_classification"],
            target["wave"],
        )
        for target in targets
    ] == [
        (
            row["target_id"],
            row["display_name"],
            row["census_geoid"],
            row["maintained_ocdid"],
            row["expected_classification"],
            row["wave"],
        )
        for row in candidates
    ]

    for row in candidates:
        nesting = row["nesting"]
        assert len(nesting["county_fips"]) == len(nesting["county_names"])
        for field in ("county_fips", "county_names", "sldu_fips", "sldl_fips"):
            assert isinstance(nesting[field], list) and nesting[field]
            assert len(nesting[field]) == len(set(nesting[field]))
        for field in ("county_fips", "sldu_fips", "sldl_fips"):
            assert all(FIPS_PATTERN.fullmatch(value) for value in nesting[field])

    by_name = {row["display_name"]: row for row in candidates}
    assert by_name["Sammamish"]["nesting"]["sldu_fips"] == [
        "005",
        "041",
        "045",
    ]
    assert by_name["Woodland"]["nesting"]["county_fips"] == ["011", "015"]
    assert by_name["Woodland"]["nesting"]["county_names"] == [
        "Clark",
        "Cowlitz",
    ]


def test_batch_1_overlap_has_exact_identity_and_nesting_parity() -> None:
    current = _json(CROSSWALK_PATH)["candidates"][:10]
    prior = {
        row["census_geoid"]: row
        for row in _json(PRIOR_CROSSWALK_PATH)["candidates"]
    }
    shared_fields = {
        "census_geoid",
        "state_fips",
        "place_fips",
        "display_name",
        "legal_name",
        "census_lsad",
        "census_classfp",
        "census_funcstat",
        "maintained_ocdid",
        "maintained_name",
        "expected_classification",
        "nesting",
    }

    assert [row["display_name"] for row in current] == [
        "Roslyn",
        "Roy",
        "Royal City",
        "Ruston",
        "St. John",
        "Sammamish",
        "SeaTac",
        "Sedro-Woolley",
        "Selah",
        "Sequim",
    ]
    for row in current:
        previous = prior[row["census_geoid"]]
        assert {field: row[field] for field in shared_fields} == {
            field: previous[field] for field in shared_fields
        }
