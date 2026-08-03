#!/usr/bin/env python3
"""Derive Gillespie County Commissioner precincts from authoritative sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz
import shapefile
from PIL import Image
from pyproj import CRS, Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform, unary_union

UA = "Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
PRECINCT_URL = (
    "https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-"
    "c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/download/precincts26p.zip"
)
MAP_URL = (
    "https://www.gillespiecounty.gov/DocumentCenter/View/1038/"
    "Gillespie-County-Commissioner-Precinct-Map-PDF"
)
MAP_SHA = "5409b6592515efe37af4bbff12a2923e782794f2bbc4d077035a8f0163f3fd70"
PRECINCT_SHA = "70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
RENDER_SIZE = (1800, 1391)
MAP_BBOX = (20.0, 174.0, 1775.0, 1049.0)
COLORS = {
    "1": (210, 249, 246),
    "2": (250, 210, 207),
    "3": (213, 249, 209),
    "4": (250, 223, 169),
}
ANCHORS = {
    "1": (1430, 390),
    "2": (390, 570),
    "3": (1200, 850),
    "4": (560, 315),
}
EXPECTED_ASSIGNMENTS = {
    "0001": "1", "0002": "2", "0003": "3", "0004": "4",
    "0005": "2", "0006": "3", "0007": "3", "0008": "1",
    "0009": "4", "0010": "2", "0012": "1", "0013": "4", "0015": "2",
}


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 6):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
            with urllib.request.urlopen(request, timeout=180) as source, path.open("wb") as target:
                shutil.copyfileobj(source, target, 1 << 20)
            if path.stat().st_size:
                return
        except Exception:
            path.unlink(missing_ok=True)
            if attempt == 5:
                raise
            time.sleep(attempt * 5)
    raise RuntimeError(url)


def repair(geometry):
    if geometry.is_empty or geometry.is_valid:
        return geometry
    try:
        from shapely.validation import make_valid
        geometry = make_valid(geometry)
    except ImportError:
        geometry = geometry.buffer(0)
    if geometry.geom_type == "GeometryCollection":
        geometry = unary_union([part for part in geometry.geoms if part.geom_type in {"Polygon", "MultiPolygon"}])
    return geometry


def pick(fields: list[str], *names: str) -> str | None:
    lookup = {field.casefold(): field for field in fields}
    return next((lookup[name.casefold()] for name in names if name.casefold() in lookup), None)


def code(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.lstrip("0") or "0"


def render_map(pdf_path: Path, output: Path) -> Image.Image:
    document = fitz.open(pdf_path)
    if len(document) != 1:
        raise ValueError(f"Expected one map page, found {len(document)}")
    page = document[0]
    zoom = RENDER_SIZE[0] / page.rect.width
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    if (pixmap.width, pixmap.height) != RENDER_SIZE:
        raise ValueError(f"Map render dimensions changed: {(pixmap.width, pixmap.height)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output)
    return Image.open(output).convert("RGB")


def load_precincts(zip_path: Path, folder: Path):
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(folder)
    shapefiles = list(folder.rglob("*.shp"))
    if len(shapefiles) != 1:
        raise ValueError(f"Expected one shapefile: {shapefiles}")
    projection = shapefiles[0].with_suffix(".prj")
    reader = shapefile.Reader(str(shapefiles[0]))
    fields = [field[0] for field in reader.fields[1:]]
    fips = pick(fields, "FIPS", "CNTY", "COUNTYFP", "COUNTY_FIP")
    county = pick(fields, "COUNTY", "COUNTYNAME", "CNTYNAME", "NAME")
    precinct = pick(fields, "PREC", "PRECINCT", "PCT", "PCTKEY", "VTD", "CNTYVTD")
    if not (fips or county) or not precinct:
        raise ValueError(f"Fields not recognized: {fields}")
    crs = CRS.from_wkt(projection.read_text(encoding="utf-8", errors="replace"))
    to_3857 = Transformer.from_crs(crs, "EPSG:3857", always_xy=True).transform
    to_4326 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform
    rows = []
    for shape_record in reader.iterShapeRecords():
        record = dict(zip(fields, shape_record.record))
        matches = (fips and code(record.get(fips)) == "171") or (county and str(record.get(county) or "").strip().casefold() == "gillespie")
        if not matches:
            continue
        geometry = repair(shape(shape_record.shape.__geo_interface__))
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(geometry.geom_type)
        rows.append({"id": str(record.get(precinct) or "").strip(), "g3857": repair(transform(to_3857, geometry)), "g4326": repair(transform(to_4326, geometry))})
    if not rows or any(not row["id"] for row in rows):
        raise ValueError("Gillespie precinct rows missing")
    return rows, {"shapefile": str(shapefiles[0].relative_to(folder)), "projection_wkt": crs.to_wkt(), "fields": fields, "fips_field": fips, "county_field": county, "precinct_field": precinct, "voting_precinct_count": len(rows)}


def pixel(point: Point, bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bounds
    left, top, right, bottom = MAP_BBOX
    return left + (point.x - min_x) / (max_x - min_x) * (right - left), bottom - (point.y - min_y) / (max_y - min_y) * (bottom - top)


def sample_points(geometry) -> list[Point]:
    points = [geometry.representative_point()]
    if geometry.contains(geometry.centroid):
        points.append(geometry.centroid)
    min_x, min_y, max_x, max_y = geometry.bounds
    for divisions in (9, 13, 17):
        for x_index in range(1, divisions):
            for y_index in range(1, divisions):
                point = Point(min_x + (max_x - min_x) * x_index / divisions, min_y + (max_y - min_y) * y_index / divisions)
                if geometry.contains(point):
                    points.append(point)
        if len(points) >= 60:
            break
    unique = {(round(point.x), round(point.y)): point for point in points}
    return list(unique.values())[:100]


def distance_squared(first: tuple[int, int, int], second: tuple[int, int, int]) -> int:
    return sum((first[index] - second[index]) ** 2 for index in range(3))


def observe(image: Image.Image, x_value: float, y_value: float):
    x_center, y_center = int(round(x_value)), int(round(y_value))
    if not (0 <= x_center < image.width and 0 <= y_center < image.height):
        return None
    best = None
    for y_pixel in range(max(0, y_center - 2), min(image.height, y_center + 3)):
        for x_pixel in range(max(0, x_center - 2), min(image.width, x_center + 3)):
            rgb = image.getpixel((x_pixel, y_pixel))[:3]
            ranked = sorted((distance_squared(rgb, color), district) for district, color in COLORS.items())
            candidate = {"district": ranked[0][1], "distance": round(math.sqrt(ranked[0][0]), 3), "separation": round(math.sqrt(ranked[1][0]) - math.sqrt(ranked[0][0]), 3), "rgb": list(rgb), "pixel": [x_pixel, y_pixel]}
            if best is None or candidate["distance"] < best["distance"]:
                best = candidate
    if best is None or best["distance"] >= 100:
        return None
    return best


def classify(image: Image.Image, geometry, bounds):
    observations = []
    for point in sample_points(geometry):
        mapped = pixel(point, bounds)
        result = observe(image, *mapped)
        if result is not None:
            result["mapped_pixel"] = [round(mapped[0], 2), round(mapped[1], 2)]
            observations.append(result)
    if not observations:
        raise ValueError("No color observations")
    counts = Counter(observation["district"] for observation in observations)
    district, count = counts.most_common(1)[0]
    dominant = [observation for observation in observations if observation["district"] == district]
    return district, count / len(observations), len(observations), statistics.fmean(observation["distance"] for observation in dominant), min(observation["separation"] for observation in dominant), observations


def rounded(value: Any):
    if isinstance(value, float):
        return round(value, 7)
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--precinct-url", default=PRECINCT_URL)
    parser.add_argument("--official-map-url", default=MAP_URL)
    parser.add_argument("--precinct-file", type=Path)
    parser.add_argument("--official-map-file", type=Path)
    arguments = parser.parse_args()
    arguments.work_dir.mkdir(parents=True, exist_ok=True)
    precinct_zip = arguments.work_dir / "precincts26p.zip"
    official_pdf = arguments.work_dir / "official-commissioner-map.pdf"
    if arguments.precinct_file:
        shutil.copyfile(arguments.precinct_file, precinct_zip)
    else:
        download(arguments.precinct_url, precinct_zip)
    if arguments.official_map_file:
        shutil.copyfile(arguments.official_map_file, official_pdf)
    else:
        download(arguments.official_map_url, official_pdf)
    precinct_hash, map_hash = digest(precinct_zip), digest(official_pdf)
    if precinct_hash != PRECINCT_SHA:
        raise ValueError(f"TLC precinct source changed: {precinct_hash}")
    if map_hash != MAP_SHA:
        raise ValueError(f"Official map changed: {map_hash}")
    image = render_map(official_pdf, arguments.work_dir / "official-commissioner-map.png")
    rows, metadata = load_precincts(precinct_zip, arguments.work_dir / "precincts")
    union_3857 = repair(unary_union([row["g3857"] for row in rows]))
    union_4326 = repair(unary_union([row["g4326"] for row in rows]))
    assignments, groups = [], defaultdict(list)
    for row in rows:
        district, confidence, count, mean_distance, minimum_separation, observations = classify(image, row["g3857"], union_3857.bounds)
        if confidence < 0.85:
            raise ValueError(f"Low confidence {row['id']}: {confidence}")
        groups[district].append(row["g4326"])
        assignments.append({"voting_precinct_id": row["id"], "commissioner_precinct": district, "confidence": round(confidence, 6), "observation_count": count, "mean_color_distance": round(mean_distance, 6), "minimum_color_separation": round(minimum_separation, 6), "observations": observations})
    actual_assignments = {assignment["voting_precinct_id"]: assignment["commissioner_precinct"] for assignment in assignments}
    if actual_assignments != EXPECTED_ASSIGNMENTS:
        raise ValueError(f"Gillespie assignment changed: {actual_assignments!r}")
    if set(groups) != {"1", "2", "3", "4"}:
        raise ValueError(sorted(groups))
    raw_features, canonical_features, dissolved, summary = [], [], [], {}
    for district in ("1", "2", "3", "4"):
        geometry = repair(unary_union(groups[district]))
        dissolved.append(geometry)
        assigned = [assignment for assignment in assignments if assignment["commissioner_precinct"] == district]
        ids = sorted((assignment["voting_precinct_id"] for assignment in assigned), key=lambda value: (len(value), value))
        confidences = [assignment["confidence"] for assignment in assigned]
        attributes = {"commissioner_precinct": district, "source_voting_precinct_count": len(ids), "source_voting_precinct_ids": ids, "assignment_confidence_min": round(min(confidences), 6), "assignment_confidence_mean": round(statistics.fmean(confidences), 6), "official_map_sha256": map_hash, "tlc_precinct_zip_sha256": precinct_hash}
        geometry_json = rounded(mapping(geometry))
        raw_features.append({"type": "Feature", "properties": attributes, "geometry": geometry_json})
        canonical_features.append({"type": "Feature", "properties": {"geometry_id": f"gillespie-county-commissioner-precinct-{district}", "record_id": f"TX:county:gillespie:commissioner_precinct:{district}", "jurisdiction_name": "Gillespie County", "district_type": "commissioner_precinct", "district_id": district, "district_name": f"Commissioner Precinct {district}", "source_agency": "Gillespie County and Texas Legislative Council", "source_layer": arguments.precinct_url, "source_request_url": arguments.precinct_url, "source_retrieved_at": arguments.retrieved_at, "source_district_field": "official_map_color_assignment", "source_attributes": attributes}, "geometry": geometry_json})
        summary[district] = attributes
    difference = union_4326.symmetric_difference(repair(unary_union(dissolved))).area
    overlap = sum(first.intersection(second).area for index, first in enumerate(dissolved) for second in dissolved[index + 1 :])
    if difference > 1e-12 or overlap > 1e-12:
        raise ValueError({"difference": difference, "overlap": overlap})
    dump(arguments.raw_output, {"type": "FeatureCollection", "features": raw_features})
    dump(arguments.output, {"type": "FeatureCollection", "features": canonical_features})
    confidences = [assignment["confidence"] for assignment in assignments]
    contract = {"derivation_type": "authoritative_composite", "official_commissioner_map_url": arguments.official_map_url, "official_commissioner_map_sha256": map_hash, "official_commissioner_map_pdf_page_count": 1, "official_commissioner_map_render_dimensions": list(RENDER_SIZE), "map_pixel_bbox": list(MAP_BBOX), "map_anchor_rgb": {key: list(value) for key, value in COLORS.items()}, "map_anchor_pixels": {key: list(value) for key, value in ANCHORS.items()}, "map_title": "Gillespie County Commissioner Precincts — Illustrative Plan 1", "map_adopted_date": "2021-11-01", "map_effective_date": "2022-01-01", "tlc_precinct_resource_url": arguments.precinct_url, "tlc_precinct_zip_sha256": precinct_hash, "tlc_precinct_metadata": metadata, "assignment_method": "Fixed 1800-pixel render of the pinned official Commissioner PDF; Web-Mercator county-bounds georeference; multi-point nearest-color classification using the closest fill pixel in a 5x5 neighborhood; dissolve of each 2026 TLC voting precinct by majority assignment.", "expected_voting_precinct_assignments": EXPECTED_ASSIGNMENTS, "assignment_confidence_min": round(min(confidences), 6), "assignment_confidence_mean": round(statistics.fmean(confidences), 6), "all_voting_precincts_assigned": len(assignments) == metadata["voting_precinct_count"], "commissioner_precinct_ids": ["1", "2", "3", "4"], "commissioner_summary": summary, "union_symmetric_difference_area_degrees": difference, "interdistrict_overlap_area_degrees": overlap, "source_hierarchy": ["Gillespie County's official Commissioner map controls district assignment.", "Texas Legislative Council 2026 primary voting precincts control exact polygon geometry.", "The county publishes the Commissioner plan as effective January 1, 2022."], "source_retrieved_at": arguments.retrieved_at}
    dump(arguments.contract_output, contract)
    dump(arguments.evidence_output, {"contract": contract, "assignments": assignments, "county_bounds_epsg3857": list(union_3857.bounds)})
    print(f"Derived 4 Gillespie County Commissioner precincts from {len(assignments)} voting precincts; min confidence {min(confidences):.3f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
