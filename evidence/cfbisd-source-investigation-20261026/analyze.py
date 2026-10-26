"""Offline CFBISD diagnostics. No acceptance thresholds or approved-data writes.

Run from the repository root after installing the optional analysis requirements:
    python evidence/cfbisd-source-investigation-20261026/analyze.py
The script refuses to replace an existing analysis or coordinate-edit record.
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.compare_tigerweb_snapshot import (
    changed_fields, compare_raw_and_canonical, drift_details,
    stable_canonical_view, stable_source_view,
)


def analyze(folder: Path) -> tuple[dict, list[dict]]:
    import pyproj
    import shapely
    from pyproj import Transformer
    from shapely.geometry import Point, shape

    def read(path: str) -> dict:
        return json.loads((folder / path).read_bytes())

    old = read("baseline/carrollton_farmers_branch_isd_districtwide.geojson")
    new = read("current/capture-1-candidate.geojson")
    second = read("current/capture-2-candidate.geojson")
    prior = read("prior-20261014/candidate.geojson")
    left = stable_source_view(old, canonical=True)
    right = stable_source_view(new, canonical=True)
    props = old["features"][0]["properties"]
    new_props = new["features"][0]["properties"]
    if left["geometry"]["type"] != "Polygon" or right["geometry"]["type"] != "Polygon":
        raise ValueError("Expected the observed Polygon geometry")
    if len(left["geometry"]["coordinates"]) != 1 or len(right["geometry"]["coordinates"]) != 1:
        raise ValueError("Expected the observed single rings")
    a = left["geometry"]["coordinates"][0]
    b = right["geometry"]["coordinates"][0]
    edits = []
    unchanged = 0
    matcher = difflib.SequenceMatcher(a=[tuple(x) for x in a], b=[tuple(x) for x in b], autojunk=False)
    for operation, start, end, fresh_start, fresh_end in matcher.get_opcodes():
        if operation == "equal":
            unchanged += end - start
            continue
        edits.append({
            "operation": operation, "ring": 0,
            "prior_index_range": [start, end], "fresh_index_range": [fresh_start, fresh_end],
            "prior_coordinates": a[start:end], "fresh_coordinates": b[fresh_start:fresh_end],
        })
    reconstructed = copy.deepcopy(left["geometry"])
    for edit in reversed(edits):
        start, end = edit["prior_index_range"]
        reconstructed["coordinates"][0][start:end] = edit["fresh_coordinates"]
    if reconstructed != right["geometry"]:
        raise ValueError("Coordinate edits do not reconstruct the candidate exactly")

    polygon_old = shape(left["geometry"])
    polygon_new = shape(right["geometry"])
    if not polygon_old.is_valid or not polygon_new.is_valid:
        raise ValueError("Invalid input polygon; no geometry repair is permitted")
    project = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
    projected_old = shapely.transform(polygon_old, project.transform, interleaved=False)
    projected_new = shapely.transform(polygon_new, project.transform, interleaved=False)
    added = projected_new.difference(projected_old)
    removed = projected_old.difference(projected_new)
    symmetric = projected_old.symmetric_difference(projected_new)
    replay = copy.deepcopy(new)
    # The existing workflow deliberately replays the baseline retrieval label.
    # This diagnostic uses that same label only in memory; capture attribution is retained.
    replay["features"][0]["properties"]["source_retrieved_at"] = props["source_retrieved_at"]
    fields = changed_fields(left["properties"], right["properties"])
    support = {}
    for label, raw, canonical in [
        ("baseline", "baseline/tigerweb-unified-school-district-4813050.geojson", "baseline/carrollton_farmers_branch_isd_districtwide.geojson"),
        ("capture_1", "current/capture-1-raw.geojson", "current/capture-1-candidate.geojson"),
        ("capture_2", "current/capture-2-raw.geojson", "current/capture-2-candidate.geojson"),
        ("october_14", "prior-20261014/raw.geojson", "prior-20261014/candidate.geojson"),
    ]:
        support[label] = compare_raw_and_canonical(folder / raw, folder / canonical)
    internal_points = []
    for label, p in [("baseline", props), ("candidate", new_props)]:
        attrs = p["source_attributes"]
        point = Point(float(attrs["INTPTLON"]), float(attrs["INTPTLAT"]))
        internal_points.append({
            "origin": label, "kind": "census_internal_point", "real_address": False,
            "coordinates": list(point.coords)[0],
            "baseline_covers": polygon_old.covers(point), "candidate_covers": polygon_new.covers(point),
        })
    changed_patches = []
    for kind, geom in [("added", polygon_new.difference(polygon_old)), ("removed", polygon_old.difference(polygon_new))]:
        parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
        for part in parts:
            if part.is_empty or part.area == 0:
                continue
            point = part.representative_point()
            changed_patches.append({
                "change": kind, "kind": "synthetic_change_probe", "real_address": False,
                "bounds_wgs84": list(part.bounds), "coordinates": list(point.coords)[0],
                "baseline_covers": polygon_old.covers(point), "candidate_covers": polygon_new.covers(point),
            })
    result = {
        "classification": "VERIFIED_CURRENT_2026_VINTAGE_WITH_GEOMETRY_AND_ATTRIBUTE_DRIFT_FROM_BASELINE_LABELED_2025",
        "baseline_vintage_independently_verified": False,
        "current_vintage_verified_by_metadata": True,
        "baseline_replacement_approved": False, "release_status": "BLOCKED_PENDING_AUTHORITY_AND_BASELINE_REVIEW",
        "legal_or_upstream_edit_cause": "UNVERIFIED", "legal_effective_date": None,
        "real_address_impact": "UNVERIFIED", "real_address_controls_available": 0,
        "geometry_id": props["geometry_id"], "record_id": props["record_id"], "geoid": props["census_geoid"],
        "baseline_vintage": props["source_vintage"], "candidate_vintage": new_props["source_vintage"],
        "source_value_deltas": {k: {"baseline": left["properties"][k], "candidate": right["properties"][k]} for k in fields},
        "unchanged_areawater_m2": right["properties"]["AREAWATER"],
        "baseline_ring_vertices_including_closure": len(a), "candidate_ring_vertices_including_closure": len(b),
        "identical_vertices_in_sequence": unchanged,
        "coordinate_edit_count": len(edits),
        "canonical_replay_drift": drift_details(stable_canonical_view(old), stable_canonical_view(replay), canonical=True),
        "capture_candidates_byte_equal": (folder / "current/capture-1-candidate.geojson").read_bytes() == (folder / "current/capture-2-candidate.geojson").read_bytes(),
        "capture_raw_responses_byte_equal": (folder / "current/capture-1-raw.geojson").read_bytes() == (folder / "current/capture-2-raw.geojson").read_bytes(),
        "independent_capture_stable_source_equal": right == stable_source_view(second, canonical=True),
        "october_14_stable_source_equal": right == stable_source_view(prior, canonical=True),
        "raw_canonical_errors": support,
        "baseline_valid": polygon_old.is_valid, "candidate_valid": polygon_new.is_valid,
        "topologically_equal": polygon_old.equals(polygon_new),
        "area_crs": "EPSG:5070", "method": "Exact source coordinates; no snapping, buffering, simplification, rounding, repair or acceptance threshold",
        "added_area_m2": added.area, "removed_area_m2": removed.area,
        "symmetric_difference_area_m2": symmetric.area,
        "symmetric_difference_pct_of_baseline": symmetric.area / projected_old.area * 100,
        "net_area_change_m2": projected_new.area - projected_old.area,
        "hausdorff_distance_m": projected_old.hausdorff_distance(projected_new),
        "census_internal_point_checks": internal_points, "synthetic_change_probes": changed_patches,
        "analysis_environment": {"python": platform.python_version(), "shapely": shapely.__version__, "geos": shapely.geos_version_string, "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str},
    }
    result["file_sha256"] = {
        str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.name not in {"analysis.json", "coordinate-edits.json"}
        and "__pycache__" not in path.parts
    }
    return result, edits


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    if any((folder / name).exists() for name in ("analysis.json", "coordinate-edits.json")):
        raise SystemExit("Analysis already exists; use a separate copy to preserve original evidence")
    result, edits = analyze(folder)
    for name, payload in [("analysis.json", result), ("coordinate-edits.json", edits)]:
        with (folder / name).open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"file_sha256", "synthetic_change_probes"}}, indent=2))
