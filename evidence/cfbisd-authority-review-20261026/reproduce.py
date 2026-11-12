"""Offline authority comparison; all outputs are review evidence, never baselines.

Use the optional analysis requirements from cfbisd-source-investigation-20261026.
To reproduce, use a disposable repository copy with the five derived outputs
omitted. Existing outputs are never overwritten by the CLI.
"""

from __future__ import annotations

import csv
import base64
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "cfbisd-source-investigation-20261026"
OUTPUTS = ("analysis.json", "address-controls.csv", "probe-comparisons.csv", "parcel-overlaps.csv", "review-overlay.geojson")


def load(path):
    return json.loads(path.read_bytes())


def analyze():
    import pyproj
    import shapely
    from pyproj import Transformer
    from shapely.geometry import Point, mapping, shape

    manifest = load(HERE / "capture-manifest.json")
    for capture in manifest["source_captures"]:
        body = (HERE / capture["package_path"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != capture["stored_sha256"]:
            raise ValueError("Stored source digest mismatch")
        if capture["storage_encoding"] == "gzip-base64":
            raw = gzip.decompress(base64.b64decode(body.strip(), validate=True))
        elif capture["storage_encoding"] == "identity":
            raw = body
        else:
            raise ValueError("Unsupported retained source encoding")
        if hashlib.sha256(raw).hexdigest() != capture["sha256"]:
            raise ValueError("Original source response digest mismatch")
    source_files = {
        "baseline": PRIOR / "baseline/carrollton_farmers_branch_isd_districtwide.geojson",
        "candidate": PRIOR / "current/capture-1-candidate.geojson",
        "tea_2025_26": HERE / "sources/tea-2026-cfbisd.geojson",
        "denton_isd": HERE / "sources/denton-cfbisd.geojson",
    }
    payloads = {key: load(path) for key, path in source_files.items()}
    if any(len(payload.get("features", [])) != 1 for payload in payloads.values()):
        raise ValueError("Each district source must contain exactly one feature")
    if payloads["tea_2025_26"]["features"][0]["properties"]["NCES_DISTR"] != "4813050":
        raise ValueError("Unexpected state district identity")
    if payloads["denton_isd"]["features"][0]["properties"]["ISD"] != "Carrollton-Farmers Branch":
        raise ValueError("Unexpected county district identity")
    geometries = {key: shape(payload["features"][0]["geometry"]) for key, payload in payloads.items()}
    if not all(geom.is_valid for geom in geometries.values()):
        raise ValueError("An input polygon is invalid; no repair is permitted")
    project = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
    projected = {key: shapely.transform(g, project.transform, interleaved=False) for key, g in geometries.items()}
    removed = projected["baseline"].difference(projected["candidate"])
    added = projected["candidate"].difference(projected["baseline"])
    counts = []
    for query in load(HERE / "query-reconciliation.json"):
        raw = (HERE / query["retained_source_file"]).read_bytes() if query["retained_source_file"] else query["feature_query_response_utf8"].encode()
        if hashlib.sha256(raw).hexdigest() != query["feature_query_capture"]["sha256"]:
            raise ValueError("Query response digest mismatch")
        response = json.loads(raw)
        if hashlib.sha256(query["count_response_utf8"].encode()).hexdigest() != query["count_query_capture"]["sha256"]:
            raise ValueError("Count response digest mismatch")
        expected = json.loads(query["count_response_utf8"])["count"]
        actual = len(response["features"])
        if response.get("exceededTransferLimit") or expected != actual:
            raise ValueError("Incomplete bounded source query")
        counts.append({"region": query["region"], "kind": query["kind"], "features": actual, "independent_count": expected})
    locator = load(HERE / "locator-responses.json")
    probe_rows = []
    locator_by_coordinates = {}
    for response in locator:
        capture = response["capture"]
        raw = response["raw_response_utf8"]
        if hashlib.sha256(raw.encode()).hexdigest() != capture["sha256"]:
            raise ValueError("Locator response digest mismatch")
        data = json.loads(raw)
        if data["status"] != "OK" or type(data["result"]["in_district"]) is not bool:
            raise ValueError("Invalid locator result")
        probe = capture["probe"]
        point = Point(probe["coordinates"])
        membership = {key: geom.covers(point) for key, geom in geometries.items()}
        membership["district_locator"] = data["result"]["in_district"]
        locator_by_coordinates[tuple(probe["coordinates"])] = membership["district_locator"]
        probe_rows.append({
            "probe_id": probe["id"], "kind": probe["kind"], "real_address": probe["real_address"],
            "longitude": point.x, "latitude": point.y, **membership,
            "census_membership_changes": membership["baseline"] != membership["candidate"],
            "legal_assignment": "UNKNOWN",
        })
    address_features = load(HERE / "sources/west-addresses.geojson")["features"]
    coordinate_counts = {}
    for feature in address_features:
        xy = tuple(feature["geometry"]["coordinates"])
        coordinate_counts[xy] = coordinate_counts.get(xy, 0) + 1
    address_rows = []
    for feature in address_features:
        attrs = feature["properties"]
        point = shape(feature["geometry"])
        xy = tuple(point.coords[0])
        membership = {key: geom.covers(point) for key, geom in geometries.items()}
        membership["district_locator"] = locator_by_coordinates[xy]
        update = attrs.get("UpdateDat")
        address_rows.append({
            "source_object_id": attrs["OBJECTID"], "address": attrs["Address"],
            "longitude": point.x, "latitude": point.y,
            "source_update_utc": datetime.fromtimestamp(update / 1000, timezone.utc).isoformat() if update is not None else "UNKNOWN",
            "duplicate_coordinate_records": coordinate_counts[xy], **membership,
            "census_membership_changes": membership["baseline"] != membership["candidate"],
            "coordinate_quality": "NOT_INDEPENDENTLY_FIELD_VERIFIED", "legal_assignment": "UNKNOWN",
        })
    parcel_rows = []
    for region in ("north", "west"):
        for feature in load(HERE / f"sources/{region}-parcels.geojson")["features"]:
            geom = shape(feature["geometry"])
            if not geom.is_valid:
                raise ValueError("Invalid parcel; no repair is permitted")
            geom = shapely.transform(geom, project.transform, interleaved=False)
            attrs = feature["properties"]
            parcel_rows.append({
                "region": region, "source_object_id": attrs["OBJECTID"], "property_id": attrs["prop_id"],
                "appraisal_year_field": attrs["prop_val_yr"], "school_code": attrs["schoolTaxingUnitCode"],
                "school_label": attrs["school"], "situs": attrs["situs"],
                "removed_coverage_overlap_m2": geom.intersection(removed).area,
                "added_coverage_overlap_m2": geom.intersection(added).area,
                "legal_assignment": "UNKNOWN",
            })
    affected_parcels = [row for row in parcel_rows if row["removed_coverage_overlap_m2"] > 0 or row["added_coverage_overlap_m2"] > 0]
    labels = {}
    for row in affected_parcels:
        key = row["school_label"] or "UNKNOWN"
        labels[key] = labels.get(key, 0) + 1
    synthetic = [row for row in probe_rows if row["kind"] == "synthetic_change_probe"]
    conflicts = [row for row in synthetic if row["candidate"] != row["tea_2025_26"] or row["candidate"] != row["denton_isd"] or row["candidate"] != row["district_locator"]]
    summary = {
        "package_id": "CFBISD-AUTH-001", "baseline_replacement_approved": False,
        "release_status": "BLOCKED_SOURCE_CONFLICT_AND_BASELINE_APPROVAL",
        "source_lineage": "UNKNOWN_POTENTIALLY_SHARED",
        "legal_cause": "UNVERIFIED", "legal_effective_date": None,
        "overall_real_address_impact": "UNVERIFIED", "exhaustive_address_inventory": False,
        "source_polygons_valid": True,
        "bounded_queries": counts,
        "synthetic_probe_count": len(synthetic), "synthetic_candidate_disagreements": len(conflicts),
        "synthetic_probes_cannot_count_as_real_addresses": True,
        "address_sample_records": len(address_rows), "address_sample_unique_coordinates": len(coordinate_counts),
        "address_sample_old_new_flips": sum(row["census_membership_changes"] for row in address_rows),
        "address_sample_all_five_publications_agree": all(len({row[k] for k in ["baseline", "candidate", "tea_2025_26", "denton_isd", "district_locator"]}) == 1 for row in address_rows),
        "address_sample_quality": "COUNTY_SOURCE_RECORDS_UPDATED_2021_NOT_FIELD_VALIDATED",
        "parcel_query_feature_count": len(parcel_rows), "parcel_query_unique_property_ids": len({row["property_id"] for row in parcel_rows}),
        "parcel_features_with_positive_changed_coverage_overlap": len(affected_parcels),
        "overlapping_parcel_labels": labels,
        "parcel_year_fields": sorted({row["appraisal_year_field"] for row in parcel_rows if row["appraisal_year_field"] is not None}),
        "parcel_year_unknown_count": sum(row["appraisal_year_field"] is None for row in parcel_rows),
        "parcel_year_is_not_legal_effective_date": True,
        "area_crs": "EPSG:5070", "diagnostics_are_not_acceptance_thresholds": True,
        "whole_polygon_symmetric_difference_m2": {
            f"{a}_vs_{b}": projected[a].symmetric_difference(projected[b]).area
            for a in ("baseline", "candidate") for b in ("tea_2025_26", "denton_isd")
        },
        "environment": {"shapely": shapely.__version__, "geos": shapely.geos_version_string, "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str},
    }
    overlay = {"type": "FeatureCollection", "features": []}
    for key, geom in geometries.items():
        overlay["features"].append({"type": "Feature", "properties": {"review_feature_id": key, "kind": "review_polygon", "baseline_replacement_approved": False}, "geometry": mapping(geom)})
    for row in probe_rows:
        overlay["features"].append({"type": "Feature", "properties": row, "geometry": {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]}})
    return summary, address_rows, probe_rows, parcel_rows, overlay


if __name__ == "__main__":
    if any((HERE / name).exists() for name in OUTPUTS):
        raise SystemExit("Derived outputs already exist; use a disposable copy")
    summary, addresses, probes, parcels, overlay = analyze()
    for name, data in [("analysis.json", summary), ("review-overlay.geojson", overlay)]:
        with (HERE / name).open("x", encoding="utf-8") as handle:
            if name.endswith(".geojson"):
                json.dump(data, handle, separators=(",", ":"), sort_keys=True)
            else:
                json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
    for name, rows in [("address-controls.csv", addresses), ("probe-comparisons.csv", probes), ("parcel-overlaps.csv", parcels)]:
        with (HERE / name).open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary, indent=2))
