"""Historical publications corroborate drift without authorizing new geometry."""
import copy
import importlib.util
import json
from pathlib import Path

from scripts.compare_tigerweb_snapshot import compare_canonical_files

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence/cfbisd-source-lineage-20261026"
CURRENT = ROOT / "evidence/cfbisd-source-investigation-20261026/current/capture-1-candidate.geojson"
spec = importlib.util.spec_from_file_location("cfbisd_source_lineage", FOLDER / "reproduce.py")
lineage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lineage)


def test_native_source_records_decode_to_exact_identity_attributes_and_coordinates():
    records = {year: lineage.read_record(FOLDER / f"cfbisd-tiger{year}-native.json") for year in (2024, 2025, 2026)}
    assert [len(item["native_points"]) for item in records.values()] == [1018, 1018, 1000]
    assert [item["attributes"]["ALAND"] for item in records.values()] == [122372374, 122372375, 122342541]
    assert {item["attributes"]["AWATER"] for item in records.values()} == {2709073}
    assert records[2024]["native_points"] == records[2025]["native_points"]
    assert records[2025]["native_points"] != records[2026]["native_points"]
    for item in records.values():
        assert item["attributes"]["GEOID"] == "4813050"
        assert item["attributes"]["UNSDLEA"] == "13050"
        assert item["attributes"]["NAME"] == "Carrollton-Farmers Branch Independent School District"
        assert item["native_parts"] == [0]


def test_rounded_publication_agreement_does_not_weaken_strict_geometry_comparison(tmp_path):
    source = lineage.read_record(FOLDER / "cfbisd-tiger2026-native.json")["native_points"]
    current = json.loads(CURRENT.read_bytes())
    ring = current["features"][0]["geometry"]["coordinates"][0]
    assert lineage.ring_signature(source) != lineage.ring_signature(ring)
    assert lineage.ring_signature(source, decimal_places=7) == lineage.ring_signature(ring, decimal_places=7)
    changed = copy.deepcopy(current)
    changed_ring = changed["features"][0]["geometry"]["coordinates"][0]
    changed_ring[20][0] += 0.000000001
    assert lineage.ring_signature(ring, decimal_places=7) == lineage.ring_signature(changed_ring, decimal_places=7)
    output = tmp_path / "sub_precision_change.geojson"
    output.write_text(json.dumps(changed))
    assert compare_canonical_files(CURRENT, output)[0].endswith("geometry changed")


def test_inventory_reports_identity_and_coverage_without_inventing_a_change_flag():
    analysis = lineage.analyze()
    assert analysis == json.loads((FOLDER / "analysis.json").read_bytes())
    workbooks = analysis["verification_workbooks"]
    inventory = workbooks["48_SD_Inventory_V.xlsx"]
    assert inventory["data_rows"] == 1018
    assert inventory["formula_cells"] == 0
    assert list(inventory["headers"].values()) == ["STATE CODE", "SDLEA", "LOGRADE", "HIGRADE", "SDLEVEL", "SDTYPE", "NAME"]
    assert inventory["target_rows"] == [{"row": 145, "cells": {"A145": "48", "B145": "13050", "C145": "PK", "D145": "12", "E145": "U", "F145": "", "G145": "Carrollton-Farmers Branch Independent School District"}}]
    counties = workbooks["48_County_Coverage_V.xlsx"]
    assert counties["data_rows"] == 1556
    assert [(r["row"], r["cells"][f"B{r['row']}"], r["cells"][f"C{r['row']}"]) for r in counties["target_rows"]] == [(338, "113", "Dallas"), (371, "121", "Denton")]
    assert analysis["baseline_reproduced_by_2024_or_2025_annual_product"] is False
    assert analysis["baseline_vintage_independently_verified"] is False
    assert analysis["legal_or_upstream_edit_cause"] == "UNVERIFIED"
    assert analysis["legal_effective_date"] is None
    assert analysis["baseline_replacement_approved"] is False
    assert analysis["release_status"] == "BLOCKED_PENDING_AUTHORITY_AND_BASELINE_REVIEW"
