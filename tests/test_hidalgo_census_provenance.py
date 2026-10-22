import csv
import json
from pathlib import Path
from scripts.compare_tigerweb_snapshot import compare_raw_and_canonical, stable_source_view

ROOT = Path(__file__).resolve().parents[1]

def test_hidalgo_county_refresh_preserves_geometry_and_records_area_changes():
    raw = ROOT / "data/raw/hidalgo-county"
    archive = raw / "archive/2026-08-02"
    county = ROOT / "data/geojson/hidalgo_county_countywide.geojson"
    old = json.loads((archive / county.name).read_text())
    current = json.loads(county.read_text())
    assert old["features"][0]["geometry"] == current["features"][0]["geometry"]
    prior = stable_source_view(old, canonical=True)
    fresh = stable_source_view(current, canonical=True)
    assert prior["properties"]["AREALAND"] == 4069433009
    assert fresh["properties"]["AREALAND"] == 4069433006
    assert prior["properties"]["AREAWATER"] == 30081128
    assert fresh["properties"]["AREAWATER"] == 30081128
    for view in (prior, fresh):
        for field in ("AREALAND", "AREAWATER"):
            view["properties"].pop(field)
    assert prior == fresh
    for folder, canonical in [(archive, archive / county.name), (raw, county)]:
        assert compare_raw_and_canonical(folder / "tigerweb-county-48215.geojson", canonical) == []
    props = current["features"][0]["properties"]
    assert props["source_vintage"] == "2026-01-01"
    assert props["source_retrieved_at"] == "2026-10-22"
    with (raw / "source-manifest.csv").open(newline="") as handle:
        row = next(r for r in csv.DictReader(handle) if r["source_id"] == "census-hidalgo-county")
    assert row["retrieved_at"] == props["source_retrieved_at"]
