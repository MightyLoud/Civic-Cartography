import csv
import json
from pathlib import Path
from scripts.compare_tigerweb_snapshot import compare_raw_and_canonical, stable_source_view

ROOT = Path(__file__).resolve().parents[1]

def test_olmos_park_census_refresh_preserves_exact_geometry_and_values():
    raw = ROOT / "data/raw/olmos-park"
    archive = raw / "archive/2026-08-01"
    county = ROOT / "data/geojson/olmos_park_citywide.geojson"
    old = json.loads((archive / county.name).read_text())
    current = json.loads(county.read_text())
    assert old["features"][0]["geometry"] == current["features"][0]["geometry"]
    assert stable_source_view(old, canonical=True) == stable_source_view(current, canonical=True)
    for folder, canonical in [(archive, archive / county.name), (raw, county)]:
        assert compare_raw_and_canonical(folder / "tigerweb-incorporated-place-4853988.geojson", canonical) == []
    props = current["features"][0]["properties"]
    assert props["source_vintage"] == "2026-01-01"
    assert props["source_retrieved_at"] == "2026-10-22"
    with (raw / "source-manifest.csv").open(newline="") as handle:
        row = next(r for r in csv.DictReader(handle) if r["source_id"] == "census-tigerweb-place")
    assert row["retrieved_at"] == props["source_retrieved_at"]
    assert row["vintage"] == props["source_vintage"]
