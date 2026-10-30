"""Keep conflicting authority evidence and limited address samples fail-closed."""

import csv
import base64
import gzip
import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/cfbisd-authority-review-20261026"
PRIOR = ROOT / "evidence/cfbisd-source-investigation-20261026"


def read(path):
    return json.loads(path.read_bytes())


def test_authority_sources_keep_exact_identity_and_response_bytes():
    for source in read(EVIDENCE / "capture-manifest.json")["source_captures"]:
        stored = (EVIDENCE / source["package_path"]).read_bytes()
        assert hashlib.sha256(stored).hexdigest() == source["stored_sha256"]
        raw = gzip.decompress(base64.b64decode(stored.strip(), validate=True)) if source["storage_encoding"] == "gzip-base64" else stored
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
    state = read(EVIDENCE / "sources/tea-2026-cfbisd.geojson")["features"]
    assert len(state) == 1
    assert state[0]["properties"]["NCES_DISTR"] == "4813050"
    county = read(EVIDENCE / "sources/denton-cfbisd.geojson")["features"]
    assert len(county) == 1
    assert county[0]["properties"]["ISD"] == "Carrollton-Farmers Branch"
    discovery = read(EVIDENCE / "source-discovery.json")
    assert "School_Districts__2026" in discovery["tea_operational_district_layer"]["url"]
    assert "Current_Districts_2023" in discovery["tea_search_widget_district_layer"]


def test_synthetic_source_conflicts_cannot_become_real_address_acceptance():
    shapes = {key: shape(read(path)["features"][0]["geometry"]) for key, path in {
        "candidate": PRIOR / "current/capture-1-candidate.geojson",
        "tea": EVIDENCE / "sources/tea-2026-cfbisd.geojson",
        "county": EVIDENCE / "sources/denton-cfbisd.geojson",
    }.items()}
    responses = read(EVIDENCE / "locator-responses.json")
    synthetic = [r for r in responses if r["capture"]["probe"]["kind"] == "synthetic_change_probe"]
    assert len(synthetic) == 4
    disagreement = 0
    for response in synthetic:
        probe = response["capture"]["probe"]
        assert probe["real_address"] is False
        point = Point(probe["coordinates"])
        assert shapes["tea"].covers(point) and shapes["county"].covers(point)
        assert json.loads(response["raw_response_utf8"])["result"]["in_district"] is True
        disagreement += not shapes["candidate"].covers(point)
    assert disagreement == 3
    status = read(EVIDENCE / "analysis.json")
    assert status["baseline_replacement_approved"] is False
    assert status["release_status"] == "BLOCKED_SOURCE_CONFLICT_AND_BASELINE_APPROVAL"
    assert status["source_lineage"] == "UNKNOWN_POTENTIALLY_SHARED"
    assert status["legal_effective_date"] is None


def test_sample_duplicates_and_source_years_do_not_imply_zero_overall_impact():
    status = read(EVIDENCE / "analysis.json")
    with (EVIDENCE / "address-controls.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == status["address_sample_records"] == 9
    assert len({(r["longitude"], r["latitude"]) for r in rows}) == status["address_sample_unique_coordinates"] == 7
    assert all(row["baseline"] == row["candidate"] for row in rows)
    assert all(row["source_update_utc"].startswith("2021-02-11") for row in rows)
    assert all(row["legal_assignment"] == "UNKNOWN" for row in rows)
    assert status["address_sample_old_new_flips"] == 0
    assert status["overall_real_address_impact"] == "UNVERIFIED"
    assert status["exhaustive_address_inventory"] is False
    assert status["parcel_year_fields"] == [2027]
    assert status["parcel_year_unknown_count"] == 1
    assert status["overlapping_parcel_labels"]["UNKNOWN"] == 1
    for query in read(EVIDENCE / "query-reconciliation.json"):
        assert hashlib.sha256(query["count_response_utf8"].encode()).hexdigest() == query["count_query_capture"]["sha256"]
        raw = (EVIDENCE / query["retained_source_file"]).read_bytes() if query["retained_source_file"] else query["feature_query_response_utf8"].encode()
        assert hashlib.sha256(raw).hexdigest() == query["feature_query_capture"]["sha256"]
        assert len(json.loads(raw)["features"]) == json.loads(query["count_response_utf8"])["count"]
