"""Compare preserved CFBISD publication records without changing source geometry.

Run from the repository root. Printed comparisons are diagnostics only.
"""
import argparse
import base64
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
import io
from pathlib import Path
import runpy
import struct
import zipfile


def read_native(record):
    raw_parts = {}
    for field in ("shape_record", "dbf_header", "dbf_record"):
        raw = base64.b64decode(record[f"raw_{field}_base64"], validate=True)
        if hashlib.sha256(raw).hexdigest() != record[f"raw_{field}_sha256"]:
            raise ValueError(f"Unexpected {field} digest in {record['year']}")
        raw_parts[field] = raw
    header, row = raw_parts["dbf_header"], raw_parts["dbf_record"]
    header_size, row_size = struct.unpack_from("<2H", header, 8)
    if (len(header), len(row)) != (header_size, row_size) or row[:1] != b" ":
        raise ValueError("Invalid retained DBF record")
    offset = 1
    attrs = {}
    for pos in range(32, header_size - 1, 32):
        field = header[pos:pos + 32]
        name = field[:11].split(b"\0")[0].decode("ascii")
        width = field[16]
        value = row[offset:offset + width].decode("ascii").strip()
        attrs[name] = int(value) if field[11] == ord("N") and value else value
        offset += width
    if attrs != record["attributes"] or attrs[record["source_id_field"]] != "4813050":
        raise ValueError("Unexpected target DBF identity or attributes")
    raw = raw_parts["shape_record"]
    shape_type = struct.unpack_from("<i", raw, 8)[0]
    parts, count = struct.unpack_from("<2i", raw, 44)
    if shape_type != 5 or parts != 1 or struct.unpack_from("<i", raw, 52)[0] != 0:
        raise ValueError("Expected a single-part Polygon record")
    if len(raw) != 56 + 16 * count or len(raw) != 8 + 2 * struct.unpack_from(">i", raw, 4)[0]:
        raise ValueError("Unexpected Polygon record length")
    points = list(struct.iter_unpack("<2d", raw[56:]))
    if points[0] != points[-1] or 'DATUM["D_North_American_1983"' not in record["source_crs_wkt"]:
        raise ValueError("Expected a closed NAD83 ring")
    return points, attrs


def quantized(points):
    return [tuple(Decimal(str(x)).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_EVEN) for x in p) for p in points]


def contains_chain(ring, chain):
    """Check ordered angular-coordinate agreement in either traversal direction."""
    loop = quantized(ring[:-1])
    target = quantized(chain)
    doubled = loop + loop
    reverse = target[::-1]
    return any(doubled[i:i + len(target)] in (target, reverse) for i in range(len(loop)))


def verify_archives(records, directory):
    """Verify the retained record slices against the original complete ZIPs."""
    for item in records.values():
        capture = item["source_capture"]
        filename = capture["url"].rsplit("/", 1)[-1]
        raw = (directory / filename).read_bytes()
        if len(raw) != capture["zip_bytes"] or hashlib.sha256(raw).hexdigest() != capture["zip_sha256"]:
            raise ValueError(f"Unexpected archive bytes for {filename}")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = {}
            for name, facts in item["zip_members"].items():
                member = archive.read(name)
                if len(member) != facts["bytes"] or hashlib.sha256(member).hexdigest() != facts["sha256"]:
                    raise ValueError(f"Unexpected member bytes for {name}")
                members[Path(name).suffix] = member
        index = item["record_index_zero_based"]
        offset, length = struct.unpack_from(">2i", members[".shx"], 100 + 8 * index)
        shape = members[".shp"][offset * 2:offset * 2 + 8 + length * 2]
        dbf = members[".dbf"]
        header_len, row_len = struct.unpack_from("<2H", dbf, 8)
        start = header_len + index * row_len
        actual = {"shape_record": shape, "dbf_header": dbf[:header_len], "dbf_record": dbf[start:start + row_len]}
        for name, value in actual.items():
            if value != base64.b64decode(item[f"raw_{name}_base64"], validate=True):
                raise ValueError(f"Retained {name} differs from {filename}")


def run(root, records_path, archives):
    lineage = root / "evidence/cfbisd-source-lineage-20261026"
    retained = root / "evidence/cfbisd-source-investigation-20261026"
    methods = runpy.run_path(str(lineage / "reproduce.py"))
    ring_signature = methods["ring_signature"]
    read_record = methods["read_record"]
    historical = json.loads(records_path.read_bytes())
    if archives is not None:
        verify_archives(historical, archives)
    rows = {year: read_native(item) for year, item in historical.items()}
    for year in (2024, 2025, 2026):
        item = read_record(lineage / f"cfbisd-tiger{year}-native.json")
        rows[str(year)] = item["native_points"], item["attributes"]
    baseline = json.loads((retained / "baseline/carrollton_farmers_branch_isd_districtwide.geojson").read_bytes())["features"][0]["geometry"]["coordinates"][0]
    fresh = json.loads((retained / "current/capture-1-candidate.geojson").read_bytes())["features"][0]["geometry"]["coordinates"][0]
    edits = json.loads((retained / "coordinate-edits.json").read_bytes())
    patches = {}
    for label, edit in zip(("inserted_vertex", "north", "west"), edits, strict=True):
        a, b = edit["prior_index_range"]
        c, d = edit["fresh_index_range"]
        old_chain, new_chain = baseline[a - 1:b + 1], fresh[c - 1:d + 1]
        if (old_chain[0], old_chain[-1]) != (new_chain[0], new_chain[-1]):
            raise ValueError(f"Unexpected changed endpoints for {label}")
        patches[label] = (old_chain, new_chain)
    exact = {year: ring_signature(points) for year, (points, _) in rows.items()}
    baseline_signature = ring_signature(baseline, decimal_places=7)
    fresh_signature = ring_signature(fresh, decimal_places=7)
    result = {}
    for year, (points, attrs) in rows.items():
        diagnostic = ring_signature(points, decimal_places=7)
        result[year] = {
            "vertices_including_closure": len(points),
            "aland_m2": attrs.get("ALAND", attrs.get("ALAND10")),
            "awater_m2": attrs.get("AWATER", attrs.get("AWATER10")),
            "exact_native_ring_matches": [other for other, sig in exact.items() if sig == exact[year] and other != year],
            "baseline_ring_matches_at_seven_decimal_places": diagnostic == baseline_signature,
            "fresh_ring_matches_at_seven_decimal_places": diagnostic == fresh_signature,
            "segment_coordinate_matches_at_seven_decimal_places": {
                label: {"baseline": contains_chain(points, old), "fresh": contains_chain(points, new)}
                for label, (old, new) in patches.items()
            },
        }
    return {"geoid": "4813050", "sources": result}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=Path(__file__).with_name("source-records.json"))
    parser.add_argument("--verify-archives", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(Path.cwd(), args.records, args.verify_archives), indent=2, sort_keys=True))
