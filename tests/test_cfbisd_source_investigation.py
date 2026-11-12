"""Preserve a blocked CFBISD candidate and retain failed-check evidence."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.compare_tigerweb_snapshot import (
    compare_canonical_files, compare_raw_and_canonical, stable_source_view,
)
from scripts.fetch_tigerweb_school_district import canonicalize

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/cfbisd-source-investigation-20261026"
BASELINE = EVIDENCE / "baseline/carrollton_farmers_branch_isd_districtwide.geojson"
CANDIDATE = EVIDENCE / "current/capture-1-candidate.geojson"


def read(path):
    return json.loads(path.read_bytes())


def test_approved_snapshots_and_recorded_evidence_bytes_are_preserved():
    provenance = read(EVIDENCE / "provenance.json")
    for item in provenance["files"]:
        current = (ROOT / item["repository_path"]).read_bytes()
        assert hashlib.sha256(current).hexdigest() == item["sha256"]
        assert current == (ROOT / item["archive_path"]).read_bytes()
    analysis = read(EVIDENCE / "analysis.json")
    assert analysis["baseline_replacement_approved"] is False
    assert analysis["release_status"] == "BLOCKED_PENDING_AUTHORITY_AND_BASELINE_REVIEW"
    assert analysis["legal_or_upstream_edit_cause"] == "UNVERIFIED"
    assert analysis["legal_effective_date"] is None
    assert analysis["real_address_controls_available"] == 0
    for name, digest in analysis["file_sha256"].items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == digest


def test_recorded_edits_exactly_reconstruct_substantive_geometry_difference():
    old = read(BASELINE)["features"][0]["geometry"]
    new = read(CANDIDATE)["features"][0]["geometry"]
    edits = read(EVIDENCE / "coordinate-edits.json")
    assert [e["operation"] for e in edits] == ["insert", "replace", "replace"]
    assert [(len(e["prior_coordinates"]), len(e["fresh_coordinates"])) for e in edits] == [(0, 1), (14, 9), (33, 17)]
    reconstructed = copy.deepcopy(old)
    for edit in reversed(edits):
        start, end = edit["prior_index_range"]
        assert reconstructed["coordinates"][edit["ring"]][start:end] == edit["prior_coordinates"]
        reconstructed["coordinates"][edit["ring"]][start:end] = edit["fresh_coordinates"]
    assert reconstructed == new
    assert len(old["coordinates"][0]) == 1020
    assert len(new["coordinates"][0]) == 1000


def test_source_captures_agree_with_prior_work_and_regenerate_exactly():
    first = read(CANDIDATE)
    prior = read(EVIDENCE / "prior-20261014/candidate.geojson")
    assert stable_source_view(first, canonical=True) == stable_source_view(prior, canonical=True)
    for number in (1, 2):
        raw = EVIDENCE / f"current/capture-{number}-raw.geojson"
        candidate = EVIDENCE / f"current/capture-{number}-candidate.geojson"
        assert compare_raw_and_canonical(raw, candidate) == []
        assert compare_canonical_files(CANDIDATE, candidate) == []
        props = read(candidate)["features"][0]["properties"]
        regenerated = canonicalize(
            read(raw), record_id=props["record_id"], geometry_id=props["geometry_id"],
            retrieved_at=props["source_retrieved_at"], request_url=props["source_request_url"],
            source_vintage=props["source_vintage"],
        )
        assert regenerated == read(candidate)
    assert (EVIDENCE / "current/capture-1-raw.geojson").read_bytes() == (EVIDENCE / "current/capture-2-raw.geojson").read_bytes()


def test_unchanged_approved_baseline_still_fails_the_exact_workflow_comparison(tmp_path):
    fresh = read(CANDIDATE)
    fresh["features"][0]["properties"]["source_retrieved_at"] = "2026-08-01"
    replay = tmp_path / "replay.geojson"
    replay.write_text(json.dumps(fresh))
    errors = compare_canonical_files(BASELINE, replay)
    assert len(errors) == 1
    assert errors[0].endswith(
        "geometry changed; source attributes changed: AREALAND, CENTLAT, CENTLON; "
        "canonical properties changed: source_vintage"
    )
    old = stable_source_view(read(BASELINE), canonical=True)["properties"]
    new = stable_source_view(fresh, canonical=True)["properties"]
    assert {k: (old[k], new[k]) for k in old if old[k] != new[k]} == {
        "AREALAND": (122372279, 122342541),
        "CENTLAT": ("+32.9460217", "+32.9460108"),
        "CENTLON": ("-096.9133555", "-096.9133531"),
    }
    assert old["AREAWATER"] == new["AREAWATER"] == 2709073


@pytest.mark.parametrize("field,value", [
    ("AREALAND", 122342542), ("CENTLAT", "+32.9460109"),
    ("CENTLON", "-096.9133532"), ("GEOID", "4813051"),
])
def test_a_future_cfbisd_attribute_change_remains_blocking(tmp_path, field, value):
    modified = read(CANDIDATE)
    modified["features"][0]["properties"]["source_attributes"][field] = value
    path = tmp_path / "changed.geojson"
    path.write_text(json.dumps(modified))
    assert f"source attributes changed: {field}" in compare_canonical_files(CANDIDATE, path)[0]


def test_cfbisd_workflow_uploads_failure_evidence_without_bypassing_comparison():
    workflow = yaml.safe_load((ROOT / ".github/workflows/validate-cfbisd-cumulative-voting.yml").read_text())
    job = workflow["jobs"]["validate-cfbisd"]
    assert not job.get("continue-on-error", False)
    steps = job["steps"]
    compare = next(s for s in steps if s["name"] == "Verify committed CFBISD boundary matches Census")
    upload = next(s for s in steps if s["name"] == "Upload CFBISD boundary check")
    assert "compare_tigerweb_snapshot.py" in compare["run"]
    assert not compare.get("continue-on-error", False)
    assert "if" not in compare
    assert "||" not in compare["run"]
    assert upload["if"] == "${{ always() }}"
    assert upload["with"]["path"] == "build/cfbisd/"
    assert upload["with"]["if-no-files-found"] == "error"
    assert steps.index(upload) > steps.index(compare)
