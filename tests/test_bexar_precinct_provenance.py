import json
from pathlib import Path
from scripts.compare_arcgis_district_snapshot import compare_raw_to_canonical, stable_attributes

ROOT = Path(__file__).resolve().parents[1]

def test_bexar_precinct_refresh_records_every_coordinate_change():
    raw = ROOT / 'data/raw/bexar-county'
    name = 'bexar_county_commissioner_precincts.geojson'
    old = json.loads((raw / 'archive/2026-08-02' / name).read_text())
    fresh = json.loads((ROOT / 'data/geojson' / name).read_text())
    recorded = json.loads((ROOT / 'evidence/bexar-precinct-reconciliation-20261022/coordinate-changes.json').read_text())
    changes = []
    def walk(a, b, path):
        if isinstance(a, list):
            assert isinstance(b, list) and len(a) == len(b)
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path + [i])
        elif a != b:
            changes.append({'path': path, 'prior': a, 'fresh': b})
    for a, b in zip(old['features'], fresh['features']):
        assert a['properties']['district_id'] == b['properties']['district_id']
        assert stable_attributes(a['properties']['source_attributes']) == stable_attributes(b['properties']['source_attributes'])
        walk(a['geometry']['coordinates'], b['geometry']['coordinates'], [str(a['properties']['district_id'])])
    assert changes == recorded
    assert len(changes) == 24
    for folder, canonical in [(raw / 'archive/2026-08-02', old), (raw, fresh)]:
        payload = json.loads((folder / 'commissioner-precincts-1-4.geojson').read_text())
        assert compare_raw_to_canonical(payload, canonical, raw_label='raw', canonical_label='canonical') == []
