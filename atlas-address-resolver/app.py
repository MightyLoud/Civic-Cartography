import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
ARCGIS_ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}/"
EL_PASO_LAYERS = [
    ("sanitation_water", "c1af3e27396949f49291d4a4e91745fe"),
    ("water_district", "dd0c224892d94eb8a840d41531518b65"),
]
CSU_QUERY = "https://maps.csu.org:6443/arcgis/rest/services/Base/MapServer/110/query"

PROVIDERS = [
    (r"\\bDONALA\\b", "government", "gov_us_co_el_paso_donala_wsd", "Donala Water & Sanitation District", "area_ref_donala_wsd_assessor_map", "sar_water_donala_wsd", ""),
    (r"\\bWIDEFIELD\\b", "government", "gov_us_co_el_paso_widefield_wsd", "Widefield Water and Sanitation District", "area_ref_widefield_wsd_assessor_map", "sar_water_widefield_wsd", ""),
    (r"\\bWOODMOOR\\b", "government", "gov_us_co_el_paso_woodmoor_water", "Woodmoor Water & Sanitation District No. 1", "area_ref_woodmoor_wsd_assessor_map", "sar_water_woodmoor_water", ""),
    (r"\\bACADEMY\\b", "government", "gov_us_co_el_paso_academy_wsd", "Academy Water and Sanitation District", "area_ref_academy_wsd_assessor_map", "sar_water_academy_wsd", ""),
    (r"\\bSECURITY\\b", "government", "gov_us_co_el_paso_security_wsd", "Security Water and Sanitation Districts", "area_ref_security_wsd_assessor_map", "sar_water_security_wsd", ""),
]

CSV_FIELDS = [
    "input_address", "matched_address", "latitude", "longitude", "geocode_status",
    "provider_type", "provider_id", "provider_name", "service_area_ref_id",
    "service_area_route_id", "action_route_id", "resolver_status",
    "evidence_method", "source_urls", "diagnostics",
]


def fetch_json(url, params=None, timeout=15):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "CivicAtlasResolver/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def geocode(address):
    data = fetch_json(CENSUS, {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    })
    match = (data.get("result", {}).get("addressMatches") or [None])[0]
    if not match:
        return None
    coords = match.get("coordinates") or {}
    return match.get("matchedAddress", ""), coords.get("y"), coords.get("x")


def item_service_url(item_id):
    return fetch_json(ARCGIS_ITEM.format(item_id), {"f": "json"}).get("url")


def point_query(service_url, lon, lat):
    url = (service_url or "").rstrip("/")
    if re.search(r"/(FeatureServer|MapServer)$", url, re.I):
        url += "/0"
    return fetch_json(url + "/query", {
        "f": "json",
        "where": "1=1",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
    }).get("features") or []


def normalized_provider(features):
    for feature in features:
        attrs = feature.get("attributes") or {}
        text = " | ".join(str(v) for v in attrs.values() if v is not None).upper()
        for provider in PROVIDERS:
            if re.search(provider[0], text, re.I):
                return provider[1:] + (text[:500],)
    return None


def in_csu(lon, lat):
    data = fetch_json(CSU_QUERY, {
        "f": "json",
        "where": "1=1",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
    })
    return bool(data.get("features"))


def resolve(address="", lat=None, lon=None):
    diagnostics = []
    matched = ""
    geocode_status = "COORDINATES_PROVIDED"

    if lat is None or lon is None:
        if not address:
            return {"input_address": "", "geocode_status": "MISSING_INPUT", "resolver_status": "UNRESOLVED"}
        try:
            match = geocode(address)
        except Exception as exc:
            match = None
            diagnostics.append(f"geocoder={type(exc).__name__}:{str(exc)[:120]}")
        if not match:
            return {
                "input_address": address,
                "geocode_status": "NO_MATCH",
                "resolver_status": "UNRESOLVED",
                "diagnostics": ";".join(diagnostics),
            }
        matched, lat, lon = match
        geocode_status = "MATCH"

    source_urls = []

    # Prefer normalized El Paso County water/sanitation districts.
    for layer_name, item_id in EL_PASO_LAYERS:
        try:
            service_url = item_service_url(item_id)
            if not service_url:
                diagnostics.append(layer_name + "_no_url")
                continue
            provider = normalized_provider(point_query(service_url, lon, lat))
            source_urls.append(f"https://www.arcgis.com/home/item.html?id={item_id}")
            if provider:
                provider_type, provider_id, provider_name, area_ref, route_id, action_route_id, raw = provider
                return {
                    "input_address": address,
                    "matched_address": matched,
                    "latitude": lat,
                    "longitude": lon,
                    "geocode_status": geocode_status,
                    "provider_type": provider_type,
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "service_area_ref_id": area_ref,
                    "service_area_route_id": route_id,
                    "action_route_id": action_route_id,
                    "resolver_status": "RESOLVED",
                    "evidence_method": f"census_geocode+el_paso_{layer_name}_polygon",
                    "source_urls": ";".join(source_urls),
                    "diagnostics": ";".join(diagnostics + [raw]),
                }
        except Exception as exc:
            diagnostics.append(f"{layer_name}={type(exc).__name__}:{str(exc)[:120]}")

    # Then check the direct CSU water service boundary.
    try:
        if in_csu(lon, lat):
            source_urls.append("https://maps.csu.org/Geocortex/Essentials/REST/sites/GIS_Public_Portal/map/mapservices/11/layers/110")
            return {
                "input_address": address,
                "matched_address": matched,
                "latitude": lat,
                "longitude": lon,
                "geocode_status": geocode_status,
                "provider_type": "body",
                "provider_id": "body_us_co_el_paso_colorado_springs_utilities",
                "provider_name": "Colorado Springs Utilities",
                "service_area_ref_id": "area_ref_csu_water_service_boundary_live",
                "service_area_route_id": "sar_water_csu_service_area",
                "action_route_id": "action_cos_water_service_interruption",
                "resolver_status": "RESOLVED",
                "evidence_method": "census_geocode+csu_water_boundary_polygon",
                "source_urls": ";".join(source_urls),
                "diagnostics": ";".join(diagnostics),
            }
    except Exception as exc:
        diagnostics.append(f"csu={type(exc).__name__}:{str(exc)[:120]}")

    return {
        "input_address": address,
        "matched_address": matched,
        "latitude": lat,
        "longitude": lon,
        "geocode_status": geocode_status,
        "provider_type": "unknown",
        "provider_id": "",
        "provider_name": "",
        "service_area_ref_id": "",
        "service_area_route_id": "",
        "action_route_id": "",
        "resolver_status": "UNRESOLVED",
        "evidence_method": "census_geocode+provider_polygon_no_match",
        "source_urls": ";".join(source_urls),
        "diagnostics": ";".join(diagnostics),
    }


class Handler(BaseHTTPRequestHandler):
    def send_text(self, status, body, content_type):
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        address = (query.get("address") or [""])[0].strip()
        lat = (query.get("lat") or [None])[0]
        lon = (query.get("lon") or [None])[0]

        try:
            lat = float(lat) if lat not in (None, "") else None
            lon = float(lon) if lon not in (None, "") else None
        except ValueError:
            return self.send_text(400, "error\nbad coordinates\n", "text/csv")

        if parsed.path == "/health":
            return self.send_text(200, json.dumps({"ok": True, "service": "atlas-address-resolver", "version": "0.1"}), "application/json")

        if parsed.path in ("/resolve.csv", "/resolve.json"):
            result = resolve(address, lat, lon)
            if parsed.path.endswith(".json"):
                return self.send_text(200, json.dumps(result), "application/json")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerow(result)
            return self.send_text(200, output.getvalue(), "text/csv")

        return self.send_text(200, json.dumps({"service": "Atlas Address Resolver", "usage": "/resolve.csv?address=..."}), "application/json")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
