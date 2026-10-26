"""Read-only publication-history diagnostics. Never writes canonical data.

python evidence/cfbisd-source-lineage-20261026/reproduce.py
Optional: --verify-archives /path/to/original/annual/zips
Optional: --output /new/path.json (refuses to replace an existing file)
No spatial tolerance, rounding or annual-product match is an acceptance gate.
"""
from __future__ import annotations

import argparse
import base64
from decimal import Decimal, ROUND_HALF_EVEN
import difflib
import hashlib
import io
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[1]
PRIOR = ROOT / "evidence/cfbisd-source-investigation-20261026"
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_record(path):
    item = json.loads(path.read_bytes())
    raw = base64.b64decode(item["raw_shape_record_base64"], validate=True)
    header = base64.b64decode(item["raw_dbf_header_base64"], validate=True)
    record = base64.b64decode(item["raw_dbf_record_base64"], validate=True)
    for key, value in (("shape_record", raw), ("dbf_header", header), ("dbf_record", record)):
        if sha(value) != item[f"raw_{key}_sha256"]:
            raise ValueError(f"Changed source bytes: {key}")
    if len(raw) != 8 + struct.unpack_from(">i", raw, 4)[0] * 2:
        raise ValueError("SHP record length mismatch")
    shape_type = struct.unpack_from("<i", raw, 8)[0]
    part_count, point_count = struct.unpack_from("<2i", raw, 44)
    parts = list(struct.unpack_from(f"<{part_count}i", raw, 52))
    start = 52 + 4 * part_count
    points = [list(struct.unpack_from("<2d", raw, start + 16 * i)) for i in range(point_count)]
    if shape_type != item["source_shape_type"] or parts != item["native_parts"] or points != item["native_points"]:
        raise ValueError("Native coordinate excerpt does not match retained SHP bytes")
    if shape_type != 5 or parts != [0] or points[0] != points[-1]:
        raise ValueError("Expected the captured single closed Polygon ring")
    header_length, record_length = struct.unpack_from("<2H", header, 8)
    if len(header) != header_length or len(record) != record_length or record[:1] != b" ":
        raise ValueError("DBF record/header mismatch")
    attrs, offset = {}, 1
    for pos in range(32, len(header) - 1, 32):
        descriptor = header[pos:pos + 32]
        name = descriptor[:11].split(b"\0")[0].decode("ascii")
        kind, width = chr(descriptor[11]), descriptor[16]
        text = record[offset:offset + width].decode("ascii").strip()
        attrs[name] = int(text) if kind == "N" and text else text
        offset += width
    if attrs != item["attributes"] or attrs["GEOID"] != "4813050":
        raise ValueError("Target identity or source attributes differ from retained DBF bytes")
    return item


def ring_signature(points, *, decimal_places=None):
    """Orientation/start-insensitive diagnostic; quantization is explicit and optional.

    Native source is NAD83 angular coordinates; TIGERweb output is EPSG:4326.
    Rounded agreement is publication corroboration, not exact/geodetic equality.
    This helper is never imported by production scripts or comparison gates.
    """
    if points[0] != points[-1]:
        raise ValueError("Expected a closed ring")
    ring = [tuple(p) for p in points[:-1]]
    if decimal_places is not None:
        quantum = Decimal(1).scaleb(-decimal_places)
        ring = [tuple(Decimal(str(x)).quantize(quantum, rounding=ROUND_HALF_EVEN) for x in p) for p in ring]
    minimum = min(ring)
    possibilities = []
    for order in (ring, list(reversed(ring))):
        for index, point in enumerate(order):
            if point == minimum:
                possibilities.append(tuple(order[index:] + order[:index]))
    return min(possibilities)


def inventory_rows(raw):
    results = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".xlsx"):
                continue
            workbook = archive.read(name)
            with zipfile.ZipFile(io.BytesIO(workbook)) as book:
                strings = []
                if "xl/sharedStrings.xml" in book.namelist():
                    strings = ["".join(t.itertext()) for t in ET.fromstring(book.read("xl/sharedStrings.xml")).findall("s:si", NS)]
                target_rows, headers, count, formulas = [], {}, 0, 0
                sheets = [n for n in book.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                if len(sheets) != 1:
                    raise ValueError("Unexpected source workbook layout")
                for row in ET.fromstring(book.read(sheets[0])).findall("s:sheetData/s:row", NS):
                    values = {}
                    for cell in row.findall("s:c", NS):
                        value = cell.findtext("s:v", default="", namespaces=NS)
                        if cell.get("t") == "s":
                            value = strings[int(value)]
                        elif cell.get("t") == "inlineStr":
                            value = "".join(cell.find("s:is", NS).itertext())
                        formulas += cell.find("s:f", NS) is not None
                        values[cell.get("r")] = value
                    if row.get("r") == "1":
                        headers = values
                    else:
                        count += 1
                    if "13050" in values.values():
                        target_rows.append({"row": int(row.get("r")), "cells": values})
                results[name] = {"sha256": sha(workbook), "bytes": len(workbook), "sheet": "sheet 1", "worksheet_part": sheets[0], "headers": headers, "data_rows": count, "formula_cells": formulas, "target_rows": target_rows}
    return results


def verify_archives(directory):
    """Optionally verify excerpts against the complete original public ZIPs."""
    for year in (2024, 2025, 2026):
        item = read_record(FOLDER / f"cfbisd-tiger{year}-native.json")
        capture = item["source_capture"]
        raw = (directory / f"tl_{year}_48_unsd.zip").read_bytes()
        if sha(raw) != capture["zip_sha256"] or len(raw) != capture["zip_bytes"]:
            raise ValueError("Annual archive hash mismatch")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            stem = f"tl_{year}_48_unsd"
            for name, facts in capture["zip_members"].items():
                member = archive.read(name)
                if sha(member) != facts["sha256"] or len(member) != facts["bytes"]:
                    raise ValueError("Annual archive member hash mismatch")
            index = capture["record_index_zero_based"]
            offset, length = struct.unpack_from(">2i", archive.read(stem + ".shx"), 100 + index * 8)
            shp = archive.read(stem + ".shp")[offset * 2:offset * 2 + 8 + length * 2]
            dbf = archive.read(stem + ".dbf")
            header_length, record_length = struct.unpack_from("<2H", dbf, 8)
            record = dbf[header_length + index * record_length:header_length + (index + 1) * record_length]
            for key, value in (("shape_record", shp), ("dbf_header", dbf[:header_length]), ("dbf_record", record)):
                if sha(value) != item[f"raw_{key}_sha256"]:
                    raise ValueError("Target record differs from complete archive")


def analyze():
    annual = {year: read_record(FOLDER / f"cfbisd-tiger{year}-native.json") for year in (2024, 2025, 2026)}
    candidate = json.loads((PRIOR / "current/capture-1-candidate.geojson").read_bytes())["features"][0]
    baseline = json.loads((PRIOR / "baseline/carrollton_farmers_branch_isd_districtwide.geojson").read_bytes())["features"][0]
    fresh_ring, old_ring = candidate["geometry"]["coordinates"][0], baseline["geometry"]["coordinates"][0]
    attrs = candidate["properties"]["source_attributes"]
    a, b = annual[2025]["native_points"], annual[2026]["native_points"]
    edits = [{"operation": op, "prior_range": [i, j], "fresh_range": [k, l]} for op, i, j, k, l in difflib.SequenceMatcher(a=[tuple(p) for p in a], b=[tuple(p) for p in b], autojunk=False).get_opcodes() if op != "equal"]
    verification_raw = base64.b64decode((FOLDER / "texas-2026-verification.zip.b64").read_bytes())
    capture = json.loads((FOLDER / "verification-capture.json").read_bytes())
    if sha(verification_raw) != capture["sha256"]:
        raise ValueError("Verification archive hash mismatch")
    return {
        "classification": "ANNUAL_2026_PUBLICATION_CORROBORATES_CURRENT_SOURCE_REVISION_CAUSE_UNVERIFIED",
        "geoid": "4813050", "record_id": candidate["properties"]["record_id"], "geometry_id": candidate["properties"]["geometry_id"],
        "annual": {str(year): {"vertices_including_closure": len(item["native_points"]), "ALAND": item["attributes"]["ALAND"], "AWATER": item["attributes"]["AWATER"], "archive_sha256": item["source_capture"]["zip_sha256"], "archive_url": item["source_capture"]["url"]} for year, item in annual.items()},
        "annual_2024_2025_native_points_exactly_equal": annual[2024]["native_points"] == annual[2025]["native_points"],
        "annual_2025_2026_exact_native_edits": edits,
        "baseline_vertices_including_closure": len(old_ring),
        "baseline_ALAND": int(baseline["properties"]["source_attributes"]["AREALAND"]),
        "baseline_vintage_independently_verified": False,
        "baseline_reproduced_by_2024_or_2025_annual_product": any(
            len(annual[year]["native_points"]) == len(old_ring)
            and annual[year]["attributes"]["ALAND"] == int(baseline["properties"]["source_attributes"]["AREALAND"])
            and ring_signature(annual[year]["native_points"]) == ring_signature(old_ring)
            for year in (2024, 2025)
        ),
        "annual_2026_current_exact_coordinate_ring_match_ignoring_start_and_direction": ring_signature(b) == ring_signature(fresh_ring),
        "annual_2026_current_7_decimal_diagnostic_ring_match": ring_signature(b, decimal_places=7) == ring_signature(fresh_ring, decimal_places=7),
        "diagnostic_limit": "NAD83 native angular coordinates versus EPSG:4326 TIGERweb output. Seven-decimal quantization, ring rotation and reversal are publication-history diagnostics only, not exact-coordinate/geodetic equality or an acceptance gate. Original doubles are preserved.",
        "annual_2026_current_exact_area_attribute_match": annual[2026]["attributes"]["ALAND"] == int(attrs["AREALAND"]) and annual[2026]["attributes"]["AWATER"] == int(attrs["AREAWATER"]),
        "verification_workbooks": inventory_rows(verification_raw),
        "inventory_limit": "Identity, grades, district level/type and county coverage only. No boundary geometry, change-reason field, correction record or legal-effective-date field. Blank SDTYPE is retained, not treated as a change flag.",
        "legal_or_upstream_edit_cause": "UNVERIFIED", "legal_effective_date": None,
        "controlling_boundary_action_or_correction_record_located": False,
        "baseline_replacement_approved": False, "release_status": "BLOCKED_PENDING_AUTHORITY_AND_BASELINE_REVIEW",
        "source_file_sha256": {p.name: sha(p.read_bytes()) for p in sorted(FOLDER.iterdir()) if p.suffix in (".json", ".b64") and p.name != "analysis.json"},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-archives", type=Path)
    args = parser.parse_args()
    if args.verify_archives:
        verify_archives(args.verify_archives)
    rendered = json.dumps(analyze(), indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(rendered)
    else:
        print(rendered, end="")
