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
    (r"\bWIDEFIELD\b", "government", "gov_us_co_el_paso_widefield_wsd", "Widefield Water and Sanitation District", "area_ref_widefield_wsd_assessor_map", "sar_water_widefield_wsd", "action_widefield_water_service_interruption"),
    (r"\bWOODMOOR\b", "government", "gov_us_co_el_paso_woodmoor_water", "Woodmoor Water & Sanitation District No. 1", "area_ref_woodmoor_wsd_assessor_map", "sar_water_woodmoor_water", "action_woodmoor_water_service_interruption"),
    (r"\bACADEMY\b", "government", "gov_us_co_el_paso_academy_wsd", "Academy Water and Sanitation District", "area_ref_academy_wsd_assessor_map", "sar_water_academy_wsd", "action_academy_water_service_request"),
    (r"\bSECURITY\b", "government", "gov_us_co_el_paso_security_wsd", "Security Water and Sanitation Districts", "area_ref_security_wsd_assessor_map", "sar_water_security_wsd", "action_security_water_service_interruption"),
    (r"\bGARDEN VALLEY\b", "government", "gov_us_co_el_paso_garden_valley_water_sanitation_district", "Garden Valley Water and Sanitation District", "area_ref_garden_valley_wsd_live_gis", "sar_water_garden_valley_wsd", ""),
    (r"\bFOREST VIEW ACRES\b", "government", "gov_us_co_el_paso_forest_view_acres_water_district", "Forest View Acres Water District", "area_ref_forest_view_acres_wd_live_gis", "sar_water_forest_view_acres_wd", "action_forest_view_acres_water_service_interruption"),
    (r"\bPARK FOREST\b", "government", "gov_us_co_el_paso_park_forest_water_district", "Park Forest Water District", "area_ref_park_forest_wd_live_gis", "sar_water_park_forest_wd", ""),
    (r"\bPIONEER LOOKOUT\b", "government", "gov_us_co_el_paso_pioneer_lookout_water_district", "Pioneer Lookout Water District", "area_ref_pioneer_lookout_wd_live_gis", "sar_water_pioneer_lookout_wd", "action_pioneer_lookout_water_service_issue"),
    (r"\bRED ROCK VALLEY ESTATES\b", "government", "gov_us_co_el_paso_red_rock_valley_estates_water_district", "Red Rock Valley Estates Water District", "area_ref_red_rock_valley_estates_wd_live_gis", "sar_water_red_rock_valley_estates_wd", ""),
    (r"\bROCK CREEK MESA\b", "government", "gov_us_co_el_paso_rock_creek_mesa_water_district", "Rock Creek Mesa Water District", "area_ref_rock_creek_mesa_wd_live_gis", "sar_water_rock_creek_mesa_wd", "action_rock_creek_mesa_water_service_interruption"),
    (r"\bSTRATMOOR HILLS\b", "government", "gov_us_co_el_paso_stratmoor_hills_water_district", "Stratmoor Hills Water District", "area_ref_stratmoor_hills_wd_live_gis", "sar_water_stratmoor_hills_wd", "action_stratmoor_hills_water_service_interruption"),
    (r"\bTURKEY CANON RANCH\b", "government", "gov_us_co_el_paso_turkey_canon_ranch_water_district", "Turkey Canon Ranch Water District", "area_ref_turkey_canon_ranch_wd_live_gis", "sar_water_turkey_canon_ranch_wd", "action_turkey_canon_water_service_request"),
]


NON_RETAIL_OVERLAYS = [
    (r"\bCHEYENNE CREEK MD PARK & WATER\b", "streamflow_water_rights_district", "gov_us_co_el_paso_cheyenne_creek_metropolitan_district", "Cheyenne Creek Metropolitan Park and Water District", "area_ref_cheyenne_creek_water_overlay_live_gis", "sar_water_cheyenne_creek_overlay", "action_cheyenne_creek_streamflow_governance_inquiry"),
    (r"\bSOUTHEASTERN COLORADO WATER CONSERVANCY\b", "regional_water_supply_authority", "gov_us_co_southeastern_colorado_water_conservancy_district", "Southeastern Colorado Water Conservancy District", "area_ref_secwcd_live_gis", "sar_water_secwcd_overlay", "action_secwcd_project_water_allocation"),
    (r"\bUPPER ARKANSAS WCD\b", "regional_augmentation_authority", "gov_us_co_upper_arkansas_water_conservancy_district", "Upper Arkansas Water Conservancy District", "area_ref_uawcd_live_gis", "sar_water_uawcd_overlay", "action_uawcd_augmentation_application"),
    (r"\bUPPER BIG SANDY GROUND WD\b", "groundwater_regulator", "gov_us_co_upper_big_sandy_ground_water_management_district", "Upper Big Sandy Ground Water Management District", "area_ref_upper_big_sandy_ground_wd_live_gis", "sar_water_upper_big_sandy_overlay", "action_upper_big_sandy_groundwater_regulatory_inquiry"),
    (r"\bUPPER BLK SQUIRREL CRK GRD WD\b", "groundwater_regulator", "gov_us_co_el_paso_upper_black_squirrel_creek_ground_water_management_district", "Upper Black Squirrel Creek Ground Water Management District", "area_ref_upper_black_squirrel_ground_wd_live_gis", "sar_water_upper_black_squirrel_overlay", "action_upper_black_squirrel_groundwater_regulatory_inquiry"),
]

CSV_FIELDS = [
    "input_address", "matched_address", "latitude", "longitude", "geocode_status",
    "provider_type", "provider_id", "provider_name", "governance_overlays", "service_area_ref_id",
    "service_area_route_id", "action_route_id", "resolver_status",
    "issue_text", "issue_domain", "issue_type", "issue_route_id", "issue_route_source",
    "issue_classifier_status", "issue_route_candidates",
    "evidence_method", "source_urls", "diagnostics",
]

ISSUE_RULES = [
    (
        "accessibility",
        "public_program_accessibility_barrier",
        [r"\bada accommodation\b", r"\baccessibility accommodation\b", r"\bdisability access\b", r"\breasonable modification\b", r"\baccessible city program\b", r"\bada grievance\b"],
        [r"\bcolorado springs\b", r"\bcity of colorado springs\b", r"\bcity program\b", r"\bcity service\b", r"\bcity facility\b", r"\bcity activity\b"],
        False,
        "institution",
        "",
        "action_cos_accessibility_public_program",
        "",
    ),
    (
        "public_records",
        "city_public_record_request",
        [r"\bcora\b", r"\bpublic records\b", r"\bopen records\b", r"\brecords request\b", r"\bcity records\b"],
        [r"\bcolorado springs\b", r"\bcity of colorado springs\b", r"\bcolorado springs city\b", r"\bcity records\b"],
        False,
        "institution",
        "",
        "action_cos_public_records_general",
        "",
    ),
    (
        "animal_services",
        "animal_cruelty_neglect_or_distress",
        [r"\banimal cruelty\b", r"\banimal abuse\b", r"\banimal neglect\b", r"\bdog attack\b", r"\bdog bite\b", r"\banimal in distress\b", r"\binjured dog\b", r"\binjured cat\b", r"\bsuffering animal\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_animal_cruelty_distress_report",
        "colorado_springs_place",
    ),
    (
        "animal_services",
        "stray_found_or_aggressive_domestic_animal",
        [r"\bstray dog\b", r"\bstray cat\b", r"\bfound dog\b", r"\bfound cat\b", r"\bloose dog\b", r"\bloose cat\b", r"\baggressive dog\b", r"\baggressive animal\b", r"\binjured stray\b", r"\buncontained animal\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_stray_found_aggressive_animal",
        "colorado_springs_place",
    ),
    (
        "animal_services",
        "dog_or_cat_license",
        [r"\bpet licen[cs]e\b", r"\bdog licen[cs]e\b", r"\bcat licen[cs]e\b", r"\blicen[cs]e my dog\b", r"\blicen[cs]e my cat\b", r"\brenew pet licen[cs]e\b", r"\brenew dog licen[cs]e\b", r"\brenew cat licen[cs]e\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_pet_license",
        "colorado_springs_place",
    ),
    (
        "transportation",
        "pothole_or_street_surface_defect",
        [r"\bpothole\b", r"\bstreet pothole\b", r"\broad pothole\b", r"\bpavement hole\b", r"\bstreet surface defect\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_pothole_report",
        "colorado_springs_place",
    ),
    (
        "transportation",
        "traffic_signal_or_sign_issue",
        [r"\btraffic signal\b", r"\btraffic light\b", r"\bpedestrian signal\b", r"\bschool flasher\b", r"\btraffic sign\b", r"\bstop sign\b", r"\bstreet sign\b", r"\bstreet marking\b", r"\bsignal timing\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_traffic_signal_sign_report",
        "colorado_springs_place",
    ),
    (
        "stormwater",
        "clogged_storm_drain_or_drainage_maintenance",
        [r"\bclogged storm drain\b", r"\bblocked storm drain\b", r"\bstorm drain clogged\b", r"\bdrainage maintenance\b", r"\bclogged inlet\b", r"\bcatch basin clogged\b", r"\bculvert blocked\b", r"\bdrainage debris\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_storm_drain_maintenance",
        "colorado_springs_place",
    ),
    (
        "transportation",
        "streetlight_outage_or_damage",
        [r"\bstreetlight out\b", r"\bstreetlight is out\b", r"\bstreet light out\b", r"\bstreet light is out\b", r"\bstreetlight outage\b", r"\bstreet light outage\b", r"\bdowned streetlight\b", r"\bbroken streetlight\b", r"\bstreetlight knocked down\b", r"\blight pole knocked down\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_streetlight_maintenance",
        "colorado_springs_place",
    ),
    (
        "code_enforcement",
        "property_code_nuisance",
        [r"\bovergrown weeds\b", r"\bovergrown vegetation\b", r"\btall weeds\b", r"\blitter (?:on|at) (?:the )?property\b", r"\bdebris (?:on|at) (?:the )?property\b", r"\btrash (?:on|at) (?:the )?property\b", r"\bgarbage (?:on|at) (?:the )?property\b", r"\bjunk outside\b", r"\bjunk (?:on|at) (?:the )?property\b", r"\boutside storage\b", r"\bjunk vehicle (?:on|at) (?:the )?property\b", r"\binoperable vehicle on private property\b", r"\brv storage violation\b", r"\bunshoveled sidewalk\b", r"\bsidewalk blocked by vegetation\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_code_enforcement_complaint",
        "colorado_springs_place",
    ),
    (
        "stormwater",
        "illegal_dumping_or_nonemergency_spill",
        [r"\billegal dumping.*storm drain\b", r"\bdumping.*storm drain\b", r"\bdumped.*storm drain\b", r"\bdumping.*into drain\b", r"\bdumped.*into drain\b", r"\bdumping.*waterway\b", r"\bdumped.*waterway\b", r"\bspill in street\b", r"\boil in street\b", r"\bconcrete wash(?: water)?\b", r"\bconstruction discharge\b", r"\bdumped yard waste\b", r"\byard waste dumped\b", r"\bnon[- ]hazardous waste\b", r"\bsmall spill\b", r"\billicit discharge\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_illicit_discharge_report",
        "colorado_springs_place",
    ),
    (
        "code_enforcement",
        "abandoned_vehicle_on_city_street",
        [r"\babandoned car\b", r"\babandoned vehicle\b", r"\bcar parked for 72 hours\b", r"\bvehicle parked over 72 hours\b", r"\bvehicle has not moved for 3 days\b", r"\bcar has not moved for 3 days\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_abandoned_street_vehicle_report",
        "colorado_springs_place",
    ),
    (
        "code_enforcement",
        "public_space_trash_or_illegal_dumping",
        [r"\billegal dumping\b", r"\billegally dumping\b", r"\bdumped (?:a )?trash\b", r"\bdumped (?:a )?debris\b", r"\btrash pile\b", r"\bdebris pile\b", r"\bgarbage dumped\b", r"\bdumped (?:a )?garbage\b", r"\btires dumped\b", r"\bdumped (?:a )?tires\b", r"\bmattress dumped\b", r"\bdumped (?:a )?mattress\b"],
        [],
        True,
        "institution",
        "",
        "action_cos_public_space_dumping_report",
        "colorado_springs_place",
    ),
    (
        "water",
        "project_water_allocation",
        [r"\bproject water\b", r"\bfryingpan[- ]arkansas\b", r"\bfry[- ]ark\b"],
        [],
        True,
        "governance_overlay",
        "regional_water_supply_authority",
        "",
        "",
    ),
    (
        "water",
        "augmentation_water_need",
        [r"\baugmentation\b", r"\breplacement water\b"],
        [],
        True,
        "governance_overlay",
        "regional_augmentation_authority",
        "",
        "",
    ),
    (
        "water",
        "cheyenne_creek_governance",
        [r"\bcheyenne creek\b"],
        [],
        True,
        "governance_overlay",
        "streamflow_water_rights_district",
        "",
        "",
    ),
    (
        "water",
        "groundwater_regulatory_question",
        [r"\bgroundwater\b", r"\bwell permit\b", r"\bwell rules?\b", r"\bwell regulation\b", r"\bgroundwater export\b", r"\bgroundwater metering\b"],
        [],
        True,
        "governance_overlay",
        "groundwater_regulator",
        "",
        "",
    ),
    (
        "water",
        "water_service_interruption",
        [r"\bno water\b", r"\bwater(?: is|'s)? out\b", r"\boutage\b", r"\blow (?:water )?pressure\b", r"\bwater main break\b", r"\bservice interruption\b", r"\bwater leak\b", r"\bwater service problem\b"],
        [],
        True,
        "provider",
        "",
        "",
        "",
    ),
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



def classify_overlays(features):
    matches = []
    seen = set()
    for feature in features:
        attrs = feature.get("attributes") or {}
        text = " | ".join(str(v) for v in attrs.values() if v is not None).upper()
        for pattern, overlay_class, object_id, object_name, area_ref, route_id, action_route_id in NON_RETAIL_OVERLAYS:
            if re.search(pattern, text, re.I) and object_id not in seen:
                seen.add(object_id)
                matches.append({
                    "resolver_class": overlay_class,
                    "object_id": object_id,
                    "object_name": object_name,
                    "service_area_ref_id": area_ref,
                    "service_area_route_id": route_id,
                    "action_route_id": action_route_id,
                })
    return matches


def encode_overlays(overlays):
    return json.dumps(overlays, separators=(",", ":"), sort_keys=True) if overlays else ""


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
    governance_overlays = []
    matched_address = ""
    geocode_status = "COORDINATES_PROVIDED"

    if latitude is None or longitude is None:
        if not address:
            return {
                "input_address": "",
                "geocode_status": "MISSING_INPUT",
                "governance_overlays": "",
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
                "governance_overlays": "",
                "resolver_status": "UNRESOLVED",
                "diagnostics": ";".join(diagnostics),
            }
        matched_address, latitude, longitude = geocoded
        geocode_status = "MATCH"

    source_urls = []

    # District-first: direct-service providers win provider dispatch, while
    # non-retail water-governance polygons are preserved separately.
    for layer_name, item_id in COUNTY_LAYERS:
        try:
            service_url = arcgis_service_url(item_id)
            if not service_url:
                diagnostics.append(layer_name + "_no_url")
                continue
            features = query_service_layers(service_url, longitude, latitude)
            for overlay in classify_overlays(features):
                if not any(existing.get("object_id") == overlay.get("object_id") for existing in governance_overlays):
                    governance_overlays.append(overlay)
            provider = normalize_provider(features)
            source_urls.append("https://www.arcgis.com/home/item.html?id=" + item_id)
            if provider:
                return {
                    "input_address": address,
                    "matched_address": matched_address,
                    "latitude": latitude,
                    "longitude": longitude,
                    "geocode_status": geocode_status,
                    **provider,
                    "governance_overlays": encode_overlays(governance_overlays),
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
                "governance_overlays": encode_overlays(governance_overlays),
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
    # polygon after local district exclusion. Governance overlays do not block a retail
    # provider; they remain visible as additional institutional context.
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
                "governance_overlays": encode_overlays(governance_overlays),
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
        "governance_overlays": encode_overlays(governance_overlays),
        "service_area_ref_id": "",
        "service_area_route_id": "",
        "action_route_id": "",
        "resolver_status": "UNRESOLVED",
        "evidence_method": "census_geocode+provider_polygon_no_match",
        "source_urls": ";".join(source_urls),
        "diagnostics": ";".join(diagnostics),
    }



def classify_issue(issue_text):
    text = (issue_text or "").strip().lower()
    if not text:
        return {
            "issue_text": "",
            "issue_domain": "",
            "issue_type": "",
            "issue_route_source": "",
            "required_overlay_class": "",
            "requires_location": False,
            "fixed_action_route_id": "",
            "required_location_scope": "",
            "issue_classifier_status": "NOT_CLASSIFIED",
        }

    for issue_domain, issue_type, patterns, context_patterns, requires_location, route_source, required_overlay_class, fixed_action_route_id, required_location_scope in ISSUE_RULES:
        if not any(re.search(pattern, text, re.I) for pattern in patterns):
            continue
        if context_patterns and not any(re.search(pattern, text, re.I) for pattern in context_patterns):
            return {
                "issue_text": issue_text,
                "issue_domain": issue_domain,
                "issue_type": issue_type,
                "issue_route_source": route_source,
                "required_overlay_class": required_overlay_class,
                "requires_location": requires_location,
                "fixed_action_route_id": fixed_action_route_id,
                "required_location_scope": required_location_scope,
                "issue_classifier_status": "NEEDS_INSTITUTION",
            }
        return {
            "issue_text": issue_text,
            "issue_domain": issue_domain,
            "issue_type": issue_type,
            "issue_route_source": route_source,
            "required_overlay_class": required_overlay_class,
            "requires_location": requires_location,
            "fixed_action_route_id": fixed_action_route_id,
            "required_location_scope": required_location_scope,
            "issue_classifier_status": "CLASSIFIED",
        }

    return {
        "issue_text": issue_text,
        "issue_domain": "",
        "issue_type": "",
        "issue_route_source": "",
        "required_overlay_class": "",
        "requires_location": False,
        "fixed_action_route_id": "",
        "required_location_scope": "",
        "issue_classifier_status": "UNSUPPORTED",
    }


def apply_issue_route(result, issue_text):
    routed = dict(result)
    classification = classify_issue(issue_text)
    routed["issue_text"] = classification.get("issue_text", "")
    routed["issue_domain"] = classification.get("issue_domain", "")
    routed["issue_type"] = classification.get("issue_type", "")
    routed["issue_route_id"] = ""
    routed["issue_route_source"] = classification.get("issue_route_source", "")
    routed["issue_classifier_status"] = classification.get("issue_classifier_status", "")
    routed["issue_route_candidates"] = ""

    status = classification.get("issue_classifier_status")
    if status in ("NOT_CLASSIFIED", "UNSUPPORTED", "NEEDS_INSTITUTION"):
        return routed

    if classification.get("requires_location"):
        if routed.get("geocode_status") == "MISSING_INPUT":
            routed["issue_classifier_status"] = "NEEDS_LOCATION"
            return routed
        if routed.get("geocode_status") == "NO_MATCH":
            routed["issue_classifier_status"] = "LOCATION_UNRESOLVED"
            return routed

        required_scope = classification.get("required_location_scope", "") or ""
        if required_scope == "colorado_springs_place":
            latitude = routed.get("latitude")
            longitude = routed.get("longitude")
            try:
                if latitude is None or longitude is None or not in_colorado_springs_place(longitude, latitude):
                    routed["issue_classifier_status"] = "NO_APPLICABLE_ROUTE"
                    return routed
            except Exception:
                routed["issue_classifier_status"] = "LOCATION_UNRESOLVED"
                return routed

    if classification.get("issue_route_source") == "institution":
        fixed_route = classification.get("fixed_action_route_id", "") or ""
        if fixed_route:
            routed["issue_route_id"] = fixed_route
            routed["issue_route_source"] = "institution"
            routed["issue_classifier_status"] = "ROUTED"
        else:
            routed["issue_classifier_status"] = "NO_APPLICABLE_ROUTE"
        return routed

    if classification.get("issue_route_source") == "provider":
        provider_id = routed.get("provider_id", "") or ""
        provider_route = routed.get("action_route_id", "") or ""
        if provider_id and provider_route:
            routed["issue_route_id"] = provider_route
            routed["issue_route_source"] = "provider"
            routed["issue_classifier_status"] = "ROUTED"
        elif provider_id:
            routed["issue_classifier_status"] = "PROCESS_BLOCKED"
        else:
            routed["issue_classifier_status"] = "NO_APPLICABLE_ROUTE"
        return routed

    overlays = json.loads(routed.get("governance_overlays") or "[]")
    required_class = classification.get("required_overlay_class", "")
    candidates = [
        {
            "object_id": overlay.get("object_id", ""),
            "resolver_class": overlay.get("resolver_class", ""),
            "action_route_id": overlay.get("action_route_id", ""),
        }
        for overlay in overlays
        if overlay.get("resolver_class") == required_class and overlay.get("action_route_id")
    ]
    routed["issue_route_candidates"] = json.dumps(candidates, separators=(",", ":"), sort_keys=True) if candidates else ""

    if len(candidates) == 1:
        routed["issue_route_id"] = candidates[0]["action_route_id"]
        routed["issue_route_source"] = "governance_overlay"
        routed["issue_classifier_status"] = "ROUTED"
    elif len(candidates) > 1:
        routed["issue_classifier_status"] = "AMBIGUOUS"
    else:
        routed["issue_classifier_status"] = "NO_APPLICABLE_ROUTE"
    return routed


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
        issue = (params.get("issue") or [""])[0].strip()
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
            result = apply_issue_route(resolve(address, lat, lon), issue)
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
