#!/usr/bin/env python3
"""Download and inspect Schleicher County precinct sources."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import fitz
import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

MAP_URL = "https://www.schleichercounty.gov/upload/page/0086/Schleicher%20Precinct%20Map.pdf"
REDISTRICTING_URL = (
    "https://www.schleichercounty.gov/upload/page/0091/"
    "Adoption%20Order%20with%20maps%20and%20tables%2011.01.2021.pdf"
)
TLC_URL = (
    "https://data.capitol.texas.gov/dataset/d04c72b9-16c4-4ab2-8c6d-"
    "c666d41e04b7/resource/33ec5b30-ee4d-424f-9769-57b87cb5e311/"
    "download/precincts26p.zip"
)
UA = "Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"
COUNTY_FIPS = "413"
COUNTY_NAME = "schleicher"


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
            time.sleep(attempt * 4)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pick(fields: list[str], *names: str) -> str | None:
    lookup = {field.casefold(): field for field in fields}
    return next((lookup[name.casefold()] for name in names if name.casefold() in lookup), None)


def code(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.lstrip("0") or "0"


def rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 7)
    if isinstance(value, list):
        return [rounded(item) for item in value]
    if isinstance(value, tuple):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def render_pdf(document: fitz.Document, folder: Path, width: int) -> list[list[int]]:
    folder.mkdir(parents=True, exist_ok=True)
    sizes = []
    for index, page in enumerate(document):
        zoom = width / page.rect.width
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pixmap.save(folder / f"page-{index + 1:02d}.png")
        sizes.append([pixmap.width, pixmap.height])
    return sizes


def main() -> int:
    output = Path("build/schleicher-county-bootstrap")
    work = output / "work"
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    map_pdf = output / "official-precinct-map.pdf"
    redistricting_pdf = output / "redistricting-order-2021.pdf"
    zip_path = work / "precincts26p.zip"
    download(MAP_URL, map_pdf)
    download(REDISTRICTING_URL, redistricting_pdf)
    download(TLC_URL, zip_path)

    map_document = fitz.open(map_pdf)
    if len(map_document) != 1:
        raise SystemExit(f"Expected one map page, found {len(map_document)}")
    map_sizes = render_pdf(map_document, output / "official-map-pages", 1800)
    map_text = "\n".join(page.get_text("text") for page in map_document)
    (output / "official-map-text.txt").write_text(map_text, encoding="utf-8")

    redistricting_document = fitz.open(redistricting_pdf)
    redistricting_sizes = render_pdf(
        redistricting_document,
        output / "redistricting-pages",
        1400,
    )
    redistricting_text = "\n\n".join(
        f"--- PAGE {index + 1} ---\n{page.get_text('text')}"
        for index, page in enumerate(redistricting_document)
    )
    (output / "redistricting-order-text.txt").write_text(
        redistricting_text,
        encoding="utf-8",
    )

    extract_dir = work / "precincts"
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    shapefiles = list(extract_dir.rglob("*.shp"))
    if len(shapefiles) != 1:
        raise SystemExit(f"Expected one shapefile, found {shapefiles}")
    shp = shapefiles[0]
    reader = shapefile.Reader(str(shp))
    fields = [field[0] for field in reader.fields[1:]]
    fips_field = pick(fields, "FIPS", "CNTY", "COUNTYFP", "COUNTY_FIP")
    county_field = pick(fields, "COUNTY", "COUNTYNAME", "CNTYNAME", "NAME")
    precinct_field = pick(fields, "PREC", "PRECINCT", "PCT", "PCTKEY", "VTD", "CNTYVTD")
    if not precinct_field or not (fips_field or county_field):
        raise SystemExit(f"Unrecognized TLC fields: {fields}")

    projection = shp.with_suffix(".prj")
    crs = CRS.from_wkt(projection.read_text(encoding="utf-8", errors="replace"))
    to_4326 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform
    features = []
    records = []
    for shape_record in reader.iterShapeRecords():
        record = dict(zip(fields, shape_record.record))
        matches = bool(fips_field and code(record.get(fips_field)) == COUNTY_FIPS)
        matches = matches or bool(
            county_field
            and str(record.get(county_field) or "").strip().casefold() == COUNTY_NAME
        )
        if not matches:
            continue
        precinct_id = str(record.get(precinct_field) or "").strip()
        geometry = transform(to_4326, shape(shape_record.shape.__geo_interface__))
        features.append({
            "type": "Feature",
            "properties": {
                "source_precinct_id": precinct_id,
                "source_attributes": record,
            },
            "geometry": rounded(mapping(geometry)),
        })
        records.append(record)

    if not features:
        raise SystemExit("No Schleicher County voting precincts found")
    payload = {"type": "FeatureCollection", "features": features}
    (output / "tlc-schleicher-voting-precincts.geojson").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    normalized_ids = sorted({
        code(feature["properties"]["source_precinct_id"])
        for feature in features
    })
    report = {
        "official_map_url": MAP_URL,
        "official_map_sha256": sha256(map_pdf),
        "official_map_bytes": map_pdf.stat().st_size,
        "official_map_page_count": len(map_document),
        "official_map_render_sizes": map_sizes,
        "official_map_text": map_text,
        "redistricting_order_url": REDISTRICTING_URL,
        "redistricting_order_sha256": sha256(redistricting_pdf),
        "redistricting_order_bytes": redistricting_pdf.stat().st_size,
        "redistricting_order_page_count": len(redistricting_document),
        "redistricting_order_render_sizes": redistricting_sizes,
        "redistricting_order_text": redistricting_text,
        "tlc_url": TLC_URL,
        "tlc_zip_sha256": sha256(zip_path),
        "tlc_zip_bytes": zip_path.stat().st_size,
        "shapefile": str(shp.relative_to(extract_dir)),
        "projection_wkt": crs.to_wkt(),
        "fields": fields,
        "fips_field": fips_field,
        "county_field": county_field,
        "precinct_field": precinct_field,
        "voting_precinct_count": len(features),
        "normalized_precinct_ids": normalized_ids,
        "records": records,
        "candidate_direct_identity_contract": normalized_ids == ["1", "2", "3", "4"],
    }
    (output / "discovery.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({
        "map_sha256": report["official_map_sha256"],
        "redistricting_sha256": report["redistricting_order_sha256"],
        "redistricting_pages": len(redistricting_document),
        "tlc_sha256": report["tlc_zip_sha256"],
        "voting_precinct_count": len(features),
        "normalized_precinct_ids": normalized_ids,
        "redistricting_text_preview": redistricting_text[:2000],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
