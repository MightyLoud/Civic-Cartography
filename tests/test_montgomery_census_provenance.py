import csv
import json
from pathlib import Path
from scripts.compare_tigerweb_snapshot import compare_raw_and_canonical, stable_source_view

ROOT = Path(__file__).resolve().parents[1]

def test_montgomery_county_refresh_preserves_geometry_and_records_area_changes():
    raw = ROOT / "data/raw/montgomery-county"
    archive = raw / "archive/2026-08-02"
    county = ROOT / "data/geojson/montgomery_county_countywide.geojson"
    old = json.loads((archive / county.name).read_text())
    current = json.loads(county.read_text())
    assert old["features"][0]["geometry"] == current["features"][0]["geometry"]
    prior = stable_source_view(old, canonical=True)
    fresh = stable_source_view(current, canonical=True)
    assert prior["properties"]["AREALAND"] == 2699229345
    assert fresh["properties"]["AREALAND"] == 2699231373
    assert prior["properties"]["AREAWATER"] == 89891730
    assert fresh["properties"]["AREAWATER"] == 89889706
    for view in (prior, fresh):
        for field in ("AREALAND", "AREAWATER"):
            view["properties"].pop(field)
    assert prior == fresh
    for folder, canonical in [(archive, archive / county.name), (raw, county)]:
        assert compare_raw_and_canonical(folder / "tigerweb-county-48339.geojson", canonical) == []
    props = current["features"][0]["properties"]
    assert props["source_vintage"] == "2026-01-01"
    assert props["source_retrieved_at"] == "2026-10-22"
    with (raw / "source-manifest.csv").open(newline="") as handle:
        row = next(r for r in csv.DictReader(handle) if r["source_id"] == "census-montgomery-county")
    assert row["retrieved_at"] == props["source_retrieved_at"]
