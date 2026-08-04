#!/usr/bin/env python3
"""Fetch Ellis County Commissioner precincts from the county's live MapServer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fetch_arcgis_districts import (
    canonicalize,
    normalize_identifier,
    normalize_polygon_geometry,
    normalize_source_properties,
    write_json,
)

PORTAL = "https://maps.co.ellis.tx.us/portal"
WEB_MAP_ITEM_ID = "05e4901568c044819986934e3715b292"
MAP_SERVICE_ITEM_ID = "484f13cc3dc64f20a64f5528ef79e035"
LAYER_URL = "https://maps.co.ellis.tx.us/arcgis/rest/services/Commissioner/Commissioner_Web_Map/MapServer/680"
LAYER_NAME = "Commissioner Precincts (2023-2032)"
DISTRICT_FIELD = "Commissioner_Pct"
EXPECTED_IDS = {"1", "2", "3", "4"}
USER_AGENT = "Civic-Cartography/0.1 (+https://github.com/MightyLoud/Civic-Cartography)"


def get_json(url: str, params: dict[str, str] | None = None) -> tuple[dict[str, Any], str]:
    if params:
        url = f"{url}?{urlencode(params)}"
    for attempt in range(1, 6):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=120) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError("ArcGIS response root must be an object")
            if payload.get("error"):
                raise ValueError(f"ArcGIS error: {payload['error']}")
            return payload, url
        except Exception:
            if attempt == 5:
                raise
            time.sleep(attempt * 3)
    raise RuntimeError("unreachable")


def confirm_portal_contract() -> dict[str, Any]:
    data_url = f"{PORTAL}/sharing/rest/content/items/{WEB_MAP_ITEM_ID}/data"
    payload, request_url = get_json(data_url, {"f": "json"})
    matches = []
    for operational in payload.get("operationalLayers", []):
        service_url = str(operational.get("url") or "")
        for layer in operational.get("layers", []):
            if str(layer.get("id")) == "680":
                matches.append({"service_url": service_url, "layer_id": 680, "title": (layer.get("popupInfo") or {}).get("title")})
    if len(matches) != 1:
        raise ValueError(f"Expected one Web Map reference to layer 680; found {len(matches)}")
    if not matches[0]["service_url"].endswith("/Commissioner_Web_Map/MapServer"):
        raise ValueError(f"Unexpected Web Map service: {matches[0]['service_url']}")
    return {"request_url": request_url, "match": matches[0]}


def fetch_native_features() -> tuple[dict[str, Any], dict[str, Any], str, int]:
    metadata, _ = get_json(LAYER_URL, {"f": "json"})
    if metadata.get("name") != LAYER_NAME:
        raise ValueError(f"Unexpected layer name: {metadata.get('name')!r}")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise ValueError(f"Unexpected geometry type: {metadata.get('geometryType')!r}")
    fields = {field.get("name") for field in metadata.get("fields", [])}
    if DISTRICT_FIELD not in fields:
        raise ValueError(f"Missing district field {DISTRICT_FIELD!r}")
    query, request_url = get_json(f"{LAYER_URL}/query", {"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326", "f": "json"})
    source_features = query.get("features")
    if not isinstance(source_features, list):
        raise ValueError("ArcGIS query response lacks a feature list")

    selected = []
    excluded_maintenance_records = 0
    for source in source_features:
        attributes = source.get("attributes")
        if not isinstance(attributes, dict):
            excluded_maintenance_records += 1
            continue
        district_id = normalize_identifier(attributes.get(DISTRICT_FIELD))
        if district_id not in EXPECTED_IDS:
            excluded_maintenance_records += 1
            continue
        geometry = source.get("geometry")
        if not isinstance(geometry, dict):
            excluded_maintenance_records += 1
            continue
        rings = geometry.get("rings")
        if not isinstance(rings, list) or not rings:
            excluded_maintenance_records += 1
            continue
        selected.append((int(district_id), {"type": "Feature", "properties": normalize_source_properties(attributes), "geometry": normalize_polygon_geometry({"type": "Polygon", "coordinates": rings})}))

    selected.sort(key=lambda item: item[0])
    found = {str(number) for number, _ in selected}
    if found != EXPECTED_IDS or len(selected) != 4:
        counts = {district_id: 0 for district_id in EXPECTED_IDS}
        for number, _ in selected:
            counts[str(number)] += 1
        raise ValueError(f"Expected precincts 1-4 exactly once; found counts {counts}")
    return {"type": "FeatureCollection", "features": [feature for _, feature in selected]}, metadata, request_url, excluded_maintenance_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-output", type=Path, required=True)
    args = parser.parse_args()
    portal_contract = confirm_portal_contract()
    raw, metadata, request_url, excluded = fetch_native_features()
    canonical = canonicalize(raw, district_field=DISTRICT_FIELD, jurisdiction_name="Ellis County", record_id_prefix="TX:county:ellis:commissioner_precinct", geometry_id_prefix="ellis-county-commissioner-precinct", source_agency="Ellis County GIS", layer_url=LAYER_URL, request_url=request_url, retrieved_at=args.retrieved_at, district_type="commissioner_precinct", district_name_prefix="Commissioner Precinct")
    contract = {"source_agency": "Ellis County GIS", "portal_url": PORTAL, "web_map_item_id": WEB_MAP_ITEM_ID, "map_service_item_id": MAP_SERVICE_ITEM_ID, "layer_url": LAYER_URL, "layer_name": metadata.get("name"), "district_field": DISTRICT_FIELD, "source_feature_count": 4, "excluded_maintenance_record_count": excluded, "commissioner_precinct_count": 4, "district_ids": ["1", "2", "3", "4"], "web_map_contract": portal_contract, "adopted_at": "2021-11-30", "effective_at": "2023-01-01", "source_retrieved_at": args.retrieved_at}
    write_json(args.raw_output, raw); write_json(args.output, canonical); write_json(args.contract_output, contract)
    print(f"Wrote four Ellis County Commissioner precinct features; excluded {excluded} maintenance record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
