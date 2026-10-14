"""Capture and measure 18 review candidates; never replace data/ baselines.

Run from this directory with a separate analysis environment containing
Shapely 2.2.0 and pyproj 3.8.0. Output paths are fixed beneath this directory.
The capture directory must not already exist, preventing accidental overwrite.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pyproj
import shapely
from shapely.geometry import Point, mapping, shape

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT))
from scripts import fetch_tigerweb_county as county
from scripts import fetch_tigerweb_place as place
from scripts import fetch_tigerweb_school_district as school
from scripts.compare_tigerweb_snapshot import compare_raw_and_canonical, stable_source_view
from scripts.tigerweb_source import fetch_source_vintage

TARGETS = [
    "travis_county_countywide", "denton_county_countywide",
    "carrollton_farmers_branch_isd_districtwide", "oak_point_citywide",
    "montgomery_county_countywide", "tarrant_county_countywide",
    "williamson_county_countywide", "harris_county_countywide",
    "fort_bend_county_countywide", "dallas_county_countywide",
    "hidalgo_county_countywide", "galveston_county_countywide",
    "kaufman_county_countywide", "collin_county_countywide",
    "arlington_citywide", "olmos_park_citywide",
    "bexar_county_countywide", "kerr_county_countywide",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, payload, *, pretty=False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2 if pretty else None,
                               allow_nan=False) + "\n", encoding="utf-8")


def request(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Civic-Cartography-reconciliation/0.1"})
    with urlopen(req, timeout=60) as response:
        return response.read()


def capture(name: str):
    baseline_path = ROOT / "data/geojson" / f"{name}.geojson"
    baseline = json.loads(baseline_path.read_text())
    props = baseline["features"][0]["properties"]
    started = datetime.now(timezone.utc).isoformat()
    body = request(props["source_request_url"])
    finished = datetime.now(timezone.utc).isoformat()
    raw = json.loads(body)
    stable_source_view(raw, canonical=False)
    if raw["features"][0]["properties"]["GEOID"] != props["census_geoid"]:
        raise ValueError(f"Unexpected source GEOID for {name}")
    return name, baseline, props, body, started, finished


def main() -> None:
    capture_dir = OUT / "capture"
    capture_dir.mkdir(exist_ok=False)
    baseline_hashes = {name: digest(ROOT / "data/geojson" / f"{name}.geojson") for name in TARGETS}
    layers = {county.LAYER_URL: county, place.LAYER_URL: place, school.LAYER_URL: school}
    vintages = {}
    for url in layers:
        layer_id = url.rsplit("/", 1)[1]
        vintages[url] = fetch_source_vintage(url)
        metadata = json.loads(request(f"{url}?f=json"))
        write(capture_dir / "metadata" / f"layer-{layer_id}-before.json", metadata, pretty=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(capture, TARGETS))
    for url in layers:
        if fetch_source_vintage(url) != vintages[url]:
            raise ValueError("Source vintage rollover during candidate capture; no candidates approved")
        write(capture_dir / "metadata" / f"layer-{url.rsplit('/', 1)[1]}-after.json",
              json.loads(request(f"{url}?f=json")), pretty=True)
    projection = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
    rows = []
    for name, baseline, props, body, started, finished in fetched:
        raw_path = capture_dir / "raw" / f"{name}.geojson"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)
        raw = json.loads(body)
        fresh = layers[props["source_layer"]].canonicalize(
            raw, record_id=props["record_id"], geometry_id=props["geometry_id"],
            request_url=props["source_request_url"], source_vintage=vintages[props["source_layer"]],
            retrieved_at=started[:10],
        )
        candidate_path = capture_dir / "candidates" / f"{name}.geojson"
        write(candidate_path, fresh)
        support_errors = compare_raw_and_canonical(raw_path, candidate_path)
        if support_errors:
            raise ValueError(support_errors)
        old_view = stable_source_view(baseline, canonical=True)
        new_view = stable_source_view(raw, canonical=False)
        a = shape(old_view["geometry"])
        b = shape(new_view["geometry"])
        if not (a.is_valid and b.is_valid):
            raise ValueError(f"Invalid polygon encountered for {name}; no repair permitted")
        pa = shapely.transform(a, projection.transform, interleaved=False)
        pb = shapely.transform(b, projection.transform, interleaved=False)
        added, removed = pb.difference(pa), pa.difference(pb)
        sym_area = added.area + removed.area
        probes = []
        features = []
        for label, part in [("added", b.difference(a)), ("removed", a.difference(b))]:
            if not part.is_empty:
                features.append({"type": "Feature", "properties": {"change": label,
                    "purpose": "diagnostic_only", "baseline_replacement_approved": False},
                    "geometry": mapping(part)})
                p = part.representative_point()
                probes.append({"kind": "synthetic_change_probe", "change": label,
                    "coordinates": [p.x, p.y], "baseline_covers": a.covers(p),
                    "candidate_covers": b.covers(p), "real_address": False})
        delta_path = capture_dir / "changes" / f"{name}.geojson"
        if features:
            write(delta_path, {"type": "FeatureCollection", "features": features})
        internal_points = []
        for label, attrs in [("baseline", old_view["properties"]), ("candidate", new_view["properties"])]:
            p = Point(float(attrs["INTPTLON"]), float(attrs["INTPTLAT"]))
            internal_points.append({"kind": "census_internal_point", "origin": label,
                "baseline_covers": a.covers(p), "candidate_covers": b.covers(p), "real_address": False})
        changed = sorted(k for k in old_view["properties"].keys() | new_view["properties"].keys()
                         if old_view["properties"].get(k) != new_view["properties"].get(k))
        cp = fresh["features"][0]["properties"]
        attribution_fields = set(props) - {"source_attributes", "source_vintage", "source_retrieved_at"}
        if any(props[k] != cp.get(k) for k in attribution_fields):
            raise ValueError(f"Candidate changed canonical identity/attribution for {name}")
        rows.append({
            "name": name, "geoid": props["census_geoid"], "record_id": props["record_id"],
            "geometry_id": props["geometry_id"], "source_request_url": props["source_request_url"],
            "capture_started_at_utc": started, "capture_finished_at_utc": finished,
            "baseline_vintage": props["source_vintage"], "candidate_vintage": cp["source_vintage"],
            "baseline_path": f"data/geojson/{name}.geojson", "baseline_sha256": baseline_hashes[name],
            "raw_path": str(raw_path.relative_to(ROOT)), "raw_sha256": digest(raw_path),
            "candidate_path": str(candidate_path.relative_to(ROOT)), "candidate_sha256": digest(candidate_path),
            "coordinates_changed": old_view["geometry"] != new_view["geometry"],
            "topologically_equal": a.equals(b), "baseline_valid": a.is_valid, "candidate_valid": b.is_valid,
            "actual_changed_source_fields": changed,
            "source_value_deltas": {k: {"baseline": old_view["properties"].get(k),
                                       "candidate": new_view["properties"].get(k)} for k in changed},
            "projected_baseline_area_m2": pa.area, "projected_candidate_area_m2": pb.area,
            "added_area_m2": added.area, "removed_area_m2": removed.area,
            "symmetric_difference_area_m2": sym_area,
            "symmetric_difference_pct_of_baseline": sym_area / pa.area * 100,
            "net_area_change_m2": pb.area - pa.area,
            "hausdorff_distance_m": pa.hausdorff_distance(pb),
            "synthetic_probes": probes, "census_internal_point_checks": internal_points,
            "raw_canonical_support_passed": True, "join_and_attribution_unchanged": True,
            "real_address_impact": "UNVERIFIED", "baseline_replacement_approved": False,
            "release_status": "BLOCKED_PENDING_BASELINE_REVIEW",
        })
        print(name, "candidate captured; baseline replacement blocked", flush=True)
    if any(digest(ROOT / "data/geojson" / f"{name}.geojson") != baseline_hashes[name] for name in TARGETS):
        raise ValueError("Approved baseline changed during preparation")
    manifest = {
        "scope": "18 TIGERweb failures associated with PR #480", "target_count": len(rows),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "area_crs": "EPSG:5070",
        "method": "exact source coordinates; no snap, buffer, tolerance, simplification or geometry repair",
        "python": platform.python_version(), "shapely": shapely.__version__,
        "geos": shapely.geos_version_string, "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str,
        "prepare_script_sha256": digest(Path(__file__)), "real_address_controls_available": 0,
        "approved_baselines_preserved": True, "baseline_replacement_approved": False,
        "rows": rows,
    }
    write(OUT / "manifest.json", manifest, pretty=True)


if __name__ == "__main__":
    main()
