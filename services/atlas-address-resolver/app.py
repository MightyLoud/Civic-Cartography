import csv
import io
import json
import os
import re
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
ARCGIS_ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}/"
COUNTY_LAYERS = [
    ("sanitation_water", "c1af3e27396949f49291d4a4e91745fe"),
    ("water_district", "dd0c224892d94eb8a840d41531518b65"),
]
CSU_WATER_QUERY = "https://maps.csu.org:6443/arcgis/rest/services/Base/MapServer/112/query"
TIGER_PLACES_QUERY = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query"
COLORADO_SPRINGS_GEOID = "0816000"
CSU_WATER_PLAN = "https://www.csu.org/hubfs/Document-Library/2022WaterEfficiencyPlan.pdf"

PROVIDERS = [
    (r"\bDONALA\b", "government", "gov_us_co_el_paso_donala_wsd", "Donala Water & Sanitation District", "area_ref_donala_wsd_assessor_map", "sar_water_donala_wsd", "action_donala_water_service_interruption"),
    (r"\bWIDEFIELD\b", "government", "gov_us_co_el_paso_widefield_wsd", "Widefield Water and Sanitation District", "area_ref_widefield_wsd_assessor_map", "sar_water_widefield_wsd", ""),
    (r"\bWOODMOOR\b", "government", "gov_us_co_el_paso_woodmoor_water", "Woodmoor Water & Sanitation District No. 1", "area_ref_woodmoor_wsd_assessor_map", "sar_water_woodmoor_water", ""),
    (r"\bACADEMY\b", "government", "gov_us_co_el_paso_academy_wsd", "Academy Water and Sanitation District", "area_ref_academy_wsd_assessor_map", "sar_water_academy_wsd", ""),
    (r"\bSECURITY\b", "government", "gov_us_co_el_paso_security_wsd", "Security Water and Sanitation Districts", "area_ref_security_wsd_assessor_map", "sar_water_security_wsd", "action_security_water_service_interruption"),
]

CSV_FIELDS = [
    "input_address", "matched_address", "latitude", "longitude", "geocode_status",
    "provider_type", "provider_id", "provider_name", "service_area_ref_id",
    "service_area_route_id", "action_route_id", "resolver_status",
    "evidence_method", "source_urls", "diagnostics",
]

SELF_TESTS = [
    ("CSU", "111 S Cascade Ave, Colorado Springs, CO 80903", "body_us_co_el_paso_colorado_springs_utilities"),
    ("DONALA", "13631 Shepard Hts, Colorado Springs, CO 80921", "gov_us_co_el_paso_donala_wsd"),
    ("SECURITY", "4613 Dancing Light Way, Colorado Springs, CO 80911", "gov_us_co_el_paso_security_wsd"),
    ("FAIL_CLOSED", "2586 Soma View, Colorado Springs, CO 80922", ""),
]


def get_json(url, params=None, timeout=15):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "CivicAtlasResolver/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode(address):
    data = get_json(CENSUS_GEOCODER, {
        "address": address,
        "benchmark": "Public_AR_Current",
        "format": "json",
    })
    matches = data.get("result", {}).get("addressMatches") or []
    if not matches:
        return None
    match = matches[0]
    coordinates = match.get("coordinates") or {}
    return match.get("matchedAddress", ""), coordinates.get("y"), coordinates.get("x")


def arcgis_service_url(item_id):
    return get_json(ARCGIS_ITEM.format(item_id), {"f": "json"}).get("url")


def query_point(layer_url, longitude, latitude):
    layer_url = (layer_url or "").rstrip("/")
    data = get_json(layer_url + "/query", {
        "f": "json",
        "where": "1=1",
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
    })
    return data.get("features") or []


def query_service_layers(service_url, longitude, latitude):
    """Query every advertised feature/map sublayer when an item URL is a service root."""
    service_url = (service_url or "").rstrip("/")
    if re.search(r"/(FeatureServer|MapServer)/\\d+$", service_url, re.I):
        return query_point(service_url, longitude, latitude)

    if re.search(r"/(FeatureServer|MapServer)$", service_url, re.I):
        metadata = get_json(service_url, {"f": "json"})
        layers = metadata.get("layers") or []
        features = []
        for layer in layers:
            layer_id = layer.get("id")
            if layer_id is None:
                continue
            features.extend(query_point(f"{service_url}/{layer_id}", longitude, latitude))
        if layers:
            return features

    return query_point(service_url, longitude, latitude)


def normalize_provider(features):
    for feature in features:
        attrs = feature.get("attributes") or {}
        text = " | ".join(str(v) for v in attrs.values() if v is not None).upper()
        for pattern, provider_type, provider_id, provider_name, area_ref, route_id, action_route in PROVIDERS:
            if re.search(pattern, text, re.I):
                return {
                    "provider_type": provider_type,
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "service_area_ref_id": area_ref,
                    "service_area_route_id": route_id,
                    "action_route_id": action_route,
                    "diagnostics": text[:500],
                }
    return None


def in_csu_water_boundary(longitude, latitude):
    data = get_json(CSU_WATER_QUERY, {
        "f": "json",
        "where": "1=1",
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
    })
    return bool(data.get("features"))


def in_colorado_springs_place(longitude, latitude):
    """Return True only when the point intersects the current Colorado Springs incorporated-place polygon."""
    data = get_json(TIGER_PLACES_QUERY, {
        "f": "json",
        "where": f"GEOID='{COLORADO_SPRINGS_GEOID}'",
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "GEOID,BASENAME",
        "returnGeometry": "false",
    })
    return any(
        str((feature.get("attributes") or {}).get("GEOID", "")) == COLORADO_SPRINGS_GEOID
        for feature in (data.get("features") or [])
    )


def resolve(address="", latitude=None, longitude=None):
    diagnostics = []
    matched_address = ""
    geocode_status = "COORDINATES_PROVIDED"

    if latitude is None or longitude is None:
        if not address:
            return {
                "input_address": "",
                "geocode_status": "MISSING_INPUT",
                "resolver_status": "UNRESOLVED",
            }
        try:
            geocoded = geocode(address)
        except Exception as exc:
            geocoded = None
            diagnostics.append(f"geocoder={type(exc).__name__}:{str(exc)[:120]}")
        if not geocoded:
            return {
                "input_address": address,
                "geocode_status": "NO_MATCH",
                "resolver_status": "UNRESOLVED",
                "diagnostics": ";".join(diagnostics),
            }
        matched_address, latitude, longitude = geocoded
        geocode_status = "MATCH"

    source_urls = []

    # District-first: a normalized local district beats a broader CSU fallback.
    for layer_name, item_id in COUNTY_LAYERS:
        try:
            service_url = arcgis_service_url(item_id)
            if not service_url:
                diagnostics.append(layer_name + "_no_url")
                continue
            provider = normalize_provider(query_service_layers(service_url, longitude, latitude))
            source_urls.append("https://www.arcgis.com/home/item.html?id=" + item_id)
            if provider:
                return {
                    "input_address": address,
                    "matched_address": matched_address,
                    "latitude": latitude,
                    "longitude": longitude,
                    "geocode_status": geocode_status,
                    **provider,
                    "resolver_status": "RESOLVED",
                    "evidence_method": "census_geocode+el_paso_" + layer_name + "_polygon",
                    "source_urls": ";".join(source_urls),
                    "diagnostics": ";".join(diagnostics + [provider.get("diagnostics", "")]),
                }
        except Exception as exc:
            diagnostics.append(f"{layer_name}={type(exc).__name__}:{str(exc)[:120]}")

    try:
        if in_csu_water_boundary(longitude, latitude):
            source_urls.append("https://maps.csu.org/Geocortex/Essentials/REST/sites/GIS_Public_Portal/map/mapservices/11/layers/112")
            return {
                "input_address": address,
                "matched_address": matched_address,
                "latitude": latitude,
                "longitude": longitude,
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
        diagnostics.append(f"csu_direct={type(exc).__name__}:{str(exc)[:120]}")

    # Bounded fallback for points inside the actual Colorado Springs incorporated-place
    # polygon after local district exclusion. This is not a mailing-address inference:
    # TIGERweb must spatially confirm GEOID 0816000. CSU's official Water Efficiency
    # Plan states that the water system serves City residents as well as some customers
    # outside City limits. Outside-city CSU service still requires direct provider evidence.
    try:
        if in_colorado_springs_place(longitude, latitude):
            source_urls.extend([
                "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4",
                CSU_WATER_PLAN,
            ])
            return {
                "input_address": address,
                "matched_address": matched_address,
                "latitude": latitude,
                "longitude": longitude,
                "geocode_status": geocode_status,
                "provider_type": "body",
                "provider_id": "body_us_co_el_paso_colorado_springs_utilities",
                "provider_name": "Colorado Springs Utilities",
                "service_area_ref_id": "area_ref_csu_water_service_boundary_live",
                "service_area_route_id": "sar_water_csu_service_area",
                "action_route_id": "action_cos_water_service_interruption",
                "resolver_status": "RESOLVED",
                "evidence_method": "census_geocode+district_exclusion+tigerweb_colorado_springs_place+csu_in_city_default",
                "source_urls": ";".join(source_urls),
                "diagnostics": ";".join(diagnostics),
            }
    except Exception as exc:
        diagnostics.append(f"tigerweb_city={type(exc).__name__}:{str(exc)[:120]}")

    return {
        "input_address": address,
        "matched_address": matched_address,
        "latitude": latitude,
        "longitude": longitude,
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


def run_self_tests():
    results = []
    for label, address, expected_provider_id in SELF_TESTS:
        try:
            result = resolve(address)
            actual = result.get("provider_id", "") or ""
            item = {
                "label": label,
                "address": address,
                "expected_provider_id": expected_provider_id,
                "actual_provider_id": actual,
                "resolver_status": result.get("resolver_status"),
                "geocode_status": result.get("geocode_status"),
                "matched_address": result.get("matched_address"),
                "evidence_method": result.get("evidence_method"),
                "diagnostics": result.get("diagnostics"),
                "ok": actual == expected_provider_id,
            }
        except Exception as exc:
            item = {
                "label": label,
                "address": address,
                "expected_provider_id": expected_provider_id,
                "error": f"{type(exc).__name__}:{exc}",
                "ok": False,
            }
        results.append(item)
        print("SELFTEST " + json.dumps(item, sort_keys=True), flush=True)
    return results


class Handler(BaseHTTPRequestHandler):
    def send_text(self, status, body, content_type):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        address = (params.get("address") or [""])[0].strip()
        lat = (params.get("lat") or [None])[0]
        lon = (params.get("lon") or [None])[0]

        try:
            lat = float(lat) if lat not in (None, "") else None
            lon = float(lon) if lon not in (None, "") else None
        except ValueError:
            return self.send_text(400, "error\nbad coordinates\n", "text/csv")

        if parsed.path == "/health":
            return self.send_text(200, json.dumps({
                "ok": True,
                "service": "atlas-address-resolver",
                "version": "0.1",
            }), "application/json")

        if parsed.path == "/selftest.json":
            return self.send_text(200, json.dumps(run_self_tests()), "application/json")

        if parsed.path in ("/resolve.csv", "/resolve.json"):
            result = resolve(address, lat, lon)
            if parsed.path.endswith(".json"):
                return self.send_text(200, json.dumps(result), "application/json")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerow(result)
            return self.send_text(200, output.getvalue(), "text/csv")

        return self.send_text(200, json.dumps({
            "service": "Atlas Address Resolver",
            "usage": "/resolve.csv?address=...",
        }), "application/json")

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler)
    threading.Thread(target=run_self_tests, daemon=True).start()
    server.serve_forever()
