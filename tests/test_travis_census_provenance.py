import csv
import json
from pathlib import Path
from scripts.compare_tigerweb_snapshot import compare_raw_and_canonical, stable_source_view

ROOT = Path(__file__).resolve().parents[1]

def test_travis_county_refresh_preserves_geometry_and_records_area_changes():
    raw = ROOT / "data/raw/travis-county"
    archive = raw / "archive/2026-08-02"
    county = ROOT / "data/geojson/travis_county_countywide.geojson"
    old = json.loads((archive / county.name).read_text())
    current = json.loads(county.read_text())
    import copy
    edits = json.loads((ROOT / "evidence/travis-tigerweb-reconciliation-20261023/coordinate-edits.json").read_text())
    geometry = copy.deepcopy(old["features"][0]["geometry"])
    assert len(edits) == 3
    for edit in reversed(edits):
        assert edit["operation"] == "insert" and edit["prior_coordinates"] == []
        start, end = edit["prior_index_range"]
        geometry["coordinates"][edit["ring"]][start:end] = edit["fresh_coordinates"]
    assert geometry == current["features"][0]["geometry"]
    prior = stable_source_view(old, canonical=True)
    fresh = stable_source_view(current, canonical=True)
    assert prior["properties"]["AREALAND"] == 2575299585
    assert fresh["properties"]["AREALAND"] == 2575354868
    assert prior["properties"]["AREAWATER"] == 79506870
    assert fresh["properties"]["AREAWATER"] == 79451592
    for view in (prior, fresh):
        for field in ("AREALAND", "AREAWATER"):
            view["properties"].pop(field)
    prior.pop("geometry")
    fresh.pop("geometry")
    assert prior == fresh
    for folder, canonical in [(archive, archive / county.name), (raw, county)]:
        assert compare_raw_and_canonical(folder / "tigerweb-county-48453.geojson", canonical) == []
    props = current["features"][0]["properties"]
    assert props["source_vintage"] == "2026-01-01"
    assert props["source_retrieved_at"] == "2026-10-23"
    with (raw / "source-manifest.csv").open(newline="") as handle:
        row = next(r for r in csv.DictReader(handle) if r["source_id"] == "census-travis-county")
    assert row["retrieved_at"] == props["source_retrieved_at"]
