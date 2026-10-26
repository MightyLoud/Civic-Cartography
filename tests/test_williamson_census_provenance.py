import csv
import json
from pathlib import Path
from scripts.compare_tigerweb_snapshot import compare_raw_and_canonical, stable_source_view

ROOT = Path(__file__).resolve().parents[1]

def test_williamson_county_refresh_preserves_geometry_and_records_area_changes():
    raw = ROOT / "data/raw/williamson-county"
    archive = raw / "archive/2026-08-02"
    county = ROOT / "data/geojson/williamson_county_countywide.geojson"
    old = json.loads((archive / county.name).read_text())
    current = json.loads(county.read_text())
    import copy
    edits = json.loads((ROOT / "evidence/williamson-tigerweb-reconciliation-20261025/coordinate-edits.json").read_text())
    geometry = copy.deepcopy(old["features"][0]["geometry"])
    assert len(edits) == 3
    for edit in reversed(edits):
        assert edit["operation"] == "insert" and edit["prior_coordinates"] == []
        start, end = edit["prior_index_range"]
        geometry["coordinates"][edit["ring"]][start:end] = edit["fresh_coordinates"]
    assert geometry == current["features"][0]["geometry"]
    prior = stable_source_view(old, canonical=True)
    fresh = stable_source_view(current, canonical=True)
    assert prior["properties"]["AREALAND"] == 2890090365
    assert fresh["properties"]["AREALAND"] == 2890092199
    assert prior["properties"]["AREAWATER"] == 41474365
    assert fresh["properties"]["AREAWATER"] == 41472527
    for view in (prior, fresh):
        for field in ("AREALAND", "AREAWATER"):
            view["properties"].pop(field)
    prior.pop("geometry")
    fresh.pop("geometry")
    assert prior == fresh
    for folder, canonical in [(archive, archive / county.name), (raw, county)]:
        assert compare_raw_and_canonical(folder / "tigerweb-county-48491.geojson", canonical) == []
    props = current["features"][0]["properties"]
    assert props["source_vintage"] == "2026-01-01"
    assert props["source_retrieved_at"] == "2026-10-25"
    with (raw / "source-manifest.csv").open(newline="") as handle:
        row = next(r for r in csv.DictReader(handle) if r["source_id"] == "census-williamson-county")
    assert row["retrieved_at"] == props["source_retrieved_at"]
