#!/usr/bin/env python3
"""Derive Schleicher County Commissioner precincts from adopted and current sources."""
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
from collections import Counter
from pathlib import Path
from typing import Any

import fitz
import shapefile
from PIL import Image
from pyproj import CRS, Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform, unary_union

UA = "Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
PRIMARY_MAP_URL = (
    "https://www.schleichercounty.gov/upload/page/0086/"
    "Schleicher%20Precinct%20Map.pdf"
)
REDISTRICTING_URL = (
    "https://www.schleichercounty.gov/upload/page/0091/"
    "Adoption%20Order%20with%20maps%20and%20tables%2011.01.2021.pdf"
)
TLC_URL = (
    "https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-"
    "c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/"
    "download/precincts26p.zip"
)
PRIMARY_MAP_SHA = "abf1a78df7f6f6bf532c454b8673eb9bc30267aedcc89131b0c70b652cf6ee19"
REDISTRICTING_SHA = "64e101b0eb131f8ca31ca16abf8975509aa67671ae87ac770e02123a8a5409db"
TLC_SHA = "70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
COUNTY_FIPS = "413"
COUNTY_NAME = "schleicher"
REDISTRICTING_PAGE_INDEX = 9
RENDER_SIZE = (1400, 1812)
MAP_BBOX = (58.0, 480.0, 1350.0, 1029.0)
COLORS = {
    "1": (202, 245, 243),
    "2": (247, 221, 188),
    "3": (221, 245, 190),
    "4": (219, 218, 246),
}
EXPECTED_ASSIGNMENTS = {"1": "1", "2": "2", "3": "3", "4": "4"}


def dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 6):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Accept-Encoding": "identity"},
            )
            with urllib.request.urlopen(request, timeout=180) as source, output.open("wb") as target:
                shutil.copyfileobj(source, target, 1 << 20)
            if output.stat().st_size:
                return
        except Exception:
            output.unlink(missing_ok=True)
            if attempt == 5:
                raise
            time.sleep(attempt * 5)


def repair(geometry):
    if geometry.is_empty or geometry.is_valid:
        return geometry
    try:
        from shapely.validation import make_valid

        geometry = make_valid(geometry)
    except ImportError:
        geometry = geometry.buffer(0)
    if geometry.geom_type == "GeometryCollection":
        geometry = unary_union(
            part
            for part in geometry.geoms
            if part.geom_type in {"Polygon", "MultiPolygon"}
        )
    return geometry


def pick(fields: list[str], *names: str) -> str | None:
    lookup = {field.casefold(): field for field in fields}
    return next(
        (lookup[name.casefold()] for name in names if name.casefold() in lookup),
        None,
    )


def code(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.lstrip("0") or "0"


def rounded(value: Any):
    if isinstance(value, float):
        return round(value, 7)
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def render_adopted_map(pdf_path: Path, output: Path) -> Image.Image:
    document = fitz.open(pdf_path)
    if len(document) != 15:
        raise ValueError(f"Adopted order page count changed: {len(document)}")
    page = document[REDISTRICTING_PAGE_INDEX]
    zoom = RENDER_SIZE[0] / page.rect.width
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    if (pixmap.width, pixmap.height) != RENDER_SIZE:
        raise ValueError(
            f"Adopted map render changed: {(pixmap.width, pixmap.height)}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output)
    return Image.open(output).convert("RGB")


def verify_primary_map(pdf_path: Path) -> None:
    document = fitz.open(pdf_path)
    if len(document) != 1:
        raise ValueError(f"Primary map page count changed: {len(document)}")


def load_precincts(zip_path: Path, folder: Path):
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(folder)
    shapefiles = list(folder.rglob("*.shp"))
    if len(shapefiles) != 1:
        raise ValueError(f"Expected one TLC shapefile: {shapefiles}")
    shp = shapefiles[0]
    projection = shp.with_suffix(".prj")
    reader = shapefile.Reader(str(shp))
    fields = [field[0] for field in reader.fields[1:]]
    fips_field = pick(fields, "FIPS", "CNTY", "COUNTYFP", "COUNTY_FIP")
    county_field = pick(fields, "COUNTY", "COUNTYNAME", "CNTYNAME", "NAME")
    precinct_field = pick(
        fields,
        "PREC",
        "PRECINCT",
        "PCT",
        "PCTKEY",
        "VTD",
        "CNTYVTD",
    )
    if not precinct_field or not (fips_field or county_field):
        raise ValueError(f"TLC fields not recognized: {fields}")
    crs = CRS.from_wkt(projection.read_text(encoding="utf-8", errors="replace"))
    to_3857 = Transformer.from_crs(crs, "EPSG:3857", always_xy=True).transform
    to_4326 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform
    rows = []
    for shape_record in reader.iterShapeRecords():
        record = dict(zip(fields, shape_record.record))
        matches = bool(fips_field and code(record.get(fips_field)) == COUNTY_FIPS)
        matches = matches or bool(
            county_field
            and str(record.get(county_field) or "").strip().casefold() == COUNTY_NAME
        )
        if not matches:
            continue
        precinct_id = code(record.get(precinct_field))
        geometry = repair(shape(shape_record.shape.__geo_interface__))
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(geometry.geom_type)
        rows.append(
            {
                "id": precinct_id,
                "source_id": str(record.get(precinct_field) or "").strip(),
                "source_attributes": record,
                "g3857": repair(transform(to_3857, geometry)),
                "g4326": repair(transform(to_4326, geometry)),
            }
        )
    ids = sorted(row["id"] for row in rows)
    if ids != ["1", "2", "3", "4"]:
        raise ValueError(f"Expected Schleicher voting precincts 1-4, received {ids}")
    metadata = {
        "shapefile": str(shp.relative_to(folder)),
        "projection_wkt": crs.to_wkt(),
        "fields": fields,
        "fips_field": fips_field,
        "county_field": county_field,
        "precinct_field": precinct_field,
        "voting_precinct_count": len(rows),
    }
    return rows, metadata


def pixel(point: Point, bounds: tuple[float, float, float, float]) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = bounds
    left, top, right, bottom = MAP_BBOX
    x_value = left + (point.x - min_x) / (max_x - min_x) * (right - left)
    y_value = bottom - (point.y - min_y) / (max_y - min_y) * (bottom - top)
    return x_value, y_value


def sample_points(geometry) -> list[Point]:
    points = [geometry.representative_point()]
    if geometry.contains(geometry.centroid):
        points.append(geometry.centroid)
    min_x, min_y, max_x, max_y = geometry.bounds
    for divisions in (9, 13, 17):
        for x_index in range(1, divisions):
            for y_index in range(1, divisions):
                point = Point(
                    min_x + (max_x - min_x) * x_index / divisions,
                    min_y + (max_y - min_y) * y_index / divisions,
                )
                if geometry.contains(point):
                    points.append(point)
        if len(points) >= 70:
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
            ranked = sorted(
                (distance_squared(rgb, color), district)
                for district, color in COLORS.items()
            )
            candidate = {
                "district": ranked[0][1],
                "distance": round(math.sqrt(ranked[0][0]), 3),
                "separation": round(
                    math.sqrt(ranked[1][0]) - math.sqrt(ranked[0][0]),
                    3,
                ),
                "rgb": list(rgb),
                "pixel": [x_pixel, y_pixel],
            }
            if best is None or candidate["distance"] < best["distance"]:
                best = candidate
    if best is None or best["distance"] >= 85:
        return None
    return best


def classify(image: Image.Image, geometry, bounds):
    observations = []
    for point in sample_points(geometry):
        mapped_pixel = pixel(point, bounds)
        result = observe(image, *mapped_pixel)
        if result is not None:
            result["mapped_pixel"] = [
                round(mapped_pixel[0], 2),
                round(mapped_pixel[1], 2),
            ]
            observations.append(result)
    if not observations:
        raise ValueError("No adopted-map color observations")
    counts = Counter(observation["district"] for observation in observations)
    district, count = counts.most_common(1)[0]
    dominant = [
        observation
        for observation in observations
        if observation["district"] == district
    ]
    return {
        "district": district,
        "confidence": count / len(observations),
        "observation_count": len(observations),
        "mean_color_distance": statistics.fmean(
            observation["distance"] for observation in dominant
        ),
        "minimum_color_separation": min(
            observation["separation"] for observation in dominant
        ),
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--primary-map-file", type=Path)
    parser.add_argument("--redistricting-file", type=Path)
    parser.add_argument("--precinct-file", type=Path)
    args = parser.parse_args()

    args.work_dir.mkdir(parents=True, exist_ok=True)
    primary_map = args.work_dir / "official-primary-map.pdf"
    redistricting_order = args.work_dir / "redistricting-order-2021.pdf"
    precinct_zip = args.work_dir / "precincts26p.zip"
    if args.primary_map_file:
        shutil.copyfile(args.primary_map_file, primary_map)
    else:
        download(PRIMARY_MAP_URL, primary_map)
    if args.redistricting_file:
        shutil.copyfile(args.redistricting_file, redistricting_order)
    else:
        download(REDISTRICTING_URL, redistricting_order)
    if args.precinct_file:
        shutil.copyfile(args.precinct_file, precinct_zip)
    else:
        download(TLC_URL, precinct_zip)

    primary_hash = digest(primary_map)
    redistricting_hash = digest(redistricting_order)
    precinct_hash = digest(precinct_zip)
    if primary_hash != PRIMARY_MAP_SHA:
        raise ValueError(f"Official primary map changed: {primary_hash}")
    if redistricting_hash != REDISTRICTING_SHA:
        raise ValueError(f"Adopted redistricting order changed: {redistricting_hash}")
    if precinct_hash != TLC_SHA:
        raise ValueError(f"TLC precinct source changed: {precinct_hash}")

    verify_primary_map(primary_map)
    adopted_image = render_adopted_map(
        redistricting_order,
        args.work_dir / "adopted-commissioner-map-page-10.png",
    )
    rows, metadata = load_precincts(
        precinct_zip,
        args.work_dir / "precincts",
    )
    union_3857 = repair(unary_union(row["g3857"] for row in rows))
    union_4326 = repair(unary_union(row["g4326"] for row in rows))

    assignments = []
    raw_features = []
    canonical_features = []
    output_geometries = []
    for row in sorted(rows, key=lambda item: item["id"]):
        result = classify(adopted_image, row["g3857"], union_3857.bounds)
        if result["confidence"] < 0.85:
            raise ValueError(
                f"Low adopted-map confidence for voting precinct {row['id']}: "
                f"{result['confidence']}"
            )
        if result["district"] != EXPECTED_ASSIGNMENTS[row["id"]]:
            raise ValueError(
                f"Voting precinct {row['id']} classified as Commissioner "
                f"Precinct {result['district']}"
            )
        district = row["id"]
        geometry = repair(row["g4326"])
        output_geometries.append(geometry)
        assignment = {
            "voting_precinct_id": row["id"],
            "source_voting_precinct_id": row["source_id"],
            "commissioner_precinct": district,
            "confidence": round(result["confidence"], 6),
            "observation_count": result["observation_count"],
            "mean_color_distance": round(result["mean_color_distance"], 6),
            "minimum_color_separation": round(
                result["minimum_color_separation"],
                6,
            ),
            "observations": result["observations"],
        }
        assignments.append(assignment)
        raw_properties = {
            "commissioner_precinct": district,
            "source_voting_precinct_count": 1,
            "source_voting_precinct_ids": [row["source_id"]],
            "assignment_confidence": assignment["confidence"],
            "official_primary_map_sha256": primary_hash,
            "adopted_redistricting_order_sha256": redistricting_hash,
            "tlc_precinct_zip_sha256": precinct_hash,
            "source_attributes": row["source_attributes"],
        }
        geometry_json = rounded(mapping(geometry))
        raw_features.append(
            {
                "type": "Feature",
                "properties": raw_properties,
                "geometry": geometry_json,
            }
        )
        canonical_features.append(
            {
                "type": "Feature",
                "properties": {
                    "geometry_id": f"schleicher-county-commissioner-precinct-{district}",
                    "record_id": f"TX:county:schleicher:commissioner_precinct:{district}",
                    "jurisdiction_name": "Schleicher County",
                    "district_type": "commissioner_precinct",
                    "district_id": district,
                    "district_name": f"Commissioner Precinct {district}",
                    "source_agency": "Schleicher County and Texas Legislative Council",
                    "source_layer": TLC_URL,
                    "source_request_url": TLC_URL,
                    "source_retrieved_at": args.retrieved_at,
                    "source_district_field": "adopted_map_color_identity",
                    "source_attributes": raw_properties,
                },
                "geometry": geometry_json,
            }
        )

    output_union = repair(unary_union(output_geometries))
    union_difference = output_union.symmetric_difference(union_4326).area
    overlap = 0.0
    for first_index, first in enumerate(output_geometries):
        for second in output_geometries[first_index + 1 :]:
            overlap += first.intersection(second).area
    if union_difference != 0.0:
        raise ValueError(f"Output union differs from source union: {union_difference}")
    if overlap != 0.0:
        raise ValueError(f"Commissioner precinct overlap: {overlap}")

    raw_payload = {"type": "FeatureCollection", "features": raw_features}
    canonical_payload = {
        "type": "FeatureCollection",
        "features": canonical_features,
    }
    dump(args.raw_output, raw_payload)
    dump(args.output, canonical_payload)

    confidences = [assignment["confidence"] for assignment in assignments]
    contract = {
        "county": "Schleicher County",
        "county_fips": COUNTY_FIPS,
        "official_primary_map_url": PRIMARY_MAP_URL,
        "official_primary_map_sha256": primary_hash,
        "official_primary_map_page_count": 1,
        "adopted_redistricting_order_url": REDISTRICTING_URL,
        "adopted_redistricting_order_sha256": redistricting_hash,
        "adopted_redistricting_order_page_count": 15,
        "adopted_commissioner_map_page_number": REDISTRICTING_PAGE_INDEX + 1,
        "adopted_map_render_size": list(RENDER_SIZE),
        "adopted_map_bbox": list(MAP_BBOX),
        "adopted_map_reference_colors": {
            district: list(color) for district, color in COLORS.items()
        },
        "tlc_precinct_url": TLC_URL,
        "tlc_precinct_zip_sha256": precinct_hash,
        "tlc_precinct_metadata": metadata,
        "identity_method": (
            "Current TLC voting precinct IDs 1-4 are independently classified "
            "against the adopted November 1, 2021 Commissioner map; the county's "
            "current 2024 primary map preserves the same four-number layout."
        ),
        "all_voting_precincts_assigned": True,
        "voting_precinct_count": len(rows),
        "commissioner_precinct_count": len(canonical_features),
        "assignment_confidence_min": round(min(confidences), 6),
        "assignment_confidence_mean": round(statistics.fmean(confidences), 6),
        "interdistrict_overlap_area_degrees": round(overlap, 12),
        "union_symmetric_difference_area_degrees": round(union_difference, 12),
        "assignments": [
            {
                key: value
                for key, value in assignment.items()
                if key != "observations"
            }
            for assignment in assignments
        ],
    }
    dump(args.contract_output, contract)
    dump(
        args.evidence_output,
        {
            "contract": contract,
            "assignments": assignments,
            "raw_output_sha256": digest(args.raw_output),
            "canonical_output_sha256": digest(args.output),
        },
    )
    print(
        json.dumps(
            {
                "voting_precincts_assigned": len(rows),
                "commissioner_precincts": len(canonical_features),
                "assignment_confidence_min": contract[
                    "assignment_confidence_min"
                ],
                "assignment_confidence_mean": contract[
                    "assignment_confidence_mean"
                ],
                "overlap": overlap,
                "union_difference": union_difference,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
