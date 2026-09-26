import json
import importlib.util
from pathlib import Path
import unittest

APP = Path(__file__).with_name("app.py")
spec = importlib.util.spec_from_file_location("atlas_address_resolver", APP)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class LiveResolverTests(unittest.TestCase):
    cases = [
        (
            "CSU",
            "111 S Cascade Ave, Colorado Springs, CO 80903",
            "body_us_co_el_paso_colorado_springs_utilities",
            "action_cos_water_service_interruption",
        ),
        (
            "DONALA",
            "13631 Shepard Hts, Colorado Springs, CO 80921",
            "gov_us_co_el_paso_donala_wsd",
            "action_donala_water_service_interruption",
        ),
        (
            "SECURITY",
            "4613 Dancing Light Way, Colorado Springs, CO 80911",
            "gov_us_co_el_paso_security_wsd",
            "action_security_water_service_interruption",
        ),
        (
            "WOODMOOR",
            "17230 Jackson Creek Pkwy, Monument, CO 80132",
            "gov_us_co_el_paso_woodmoor_water",
            "action_woodmoor_water_service_interruption",
        ),
        (
            "ACADEMY",
            "980 Tari Dr, Colorado Springs, CO 80921",
            "gov_us_co_el_paso_academy_wsd",
            "action_academy_water_service_request",
        ),
        (
            "FAIL_CLOSED",
            "2586 Soma View, Colorado Springs, CO 80922",
            "",
            "",
        ),
    ]

    expected_raw_layer_values = {
        "sanitation_water": {
            "ACADEMY SWD",
            "DONALA SWD AREA A",
            "DONALA SWD AREA B",
            "GARDEN VALLEY SWD",
            "WIDEFIELD SWD",
            "WOODMOOR SWD",
        },
        "water_district": {
            "CHEYENNE CREEK MD PARK & WATER",
            "FOREST VIEW ACRES WD",
            "PARK FOREST WD",
            "PIONEER LOOKOUT WD",
            "RED ROCK VALLEY ESTATES WD",
            "ROCK CREEK MESA WD",
            "SECURITY WD",
            "SOUTHEASTERN COLORADO WATER CONSERVANCY",
            "STRATMOOR HILLS WD",
            "TURKEY CANON RANCH WD",
            "UPPER ARKANSAS WCD",
            "UPPER BIG SANDY GROUND WD",
            "UPPER BLK SQUIRREL CRK GRD WD",
        },
    }

    expected_nonretail = {
        "CHEYENNE CREEK MD PARK & WATER": ("streamflow_water_rights_district", "gov_us_co_el_paso_cheyenne_creek_metropolitan_district", "action_cheyenne_creek_streamflow_governance_inquiry"),
        "SOUTHEASTERN COLORADO WATER CONSERVANCY": ("regional_water_supply_authority", "gov_us_co_southeastern_colorado_water_conservancy_district", "action_secwcd_project_water_allocation"),
        "UPPER ARKANSAS WCD": ("regional_augmentation_authority", "gov_us_co_upper_arkansas_water_conservancy_district", "action_uawcd_augmentation_application"),
        "UPPER BIG SANDY GROUND WD": ("groundwater_regulator", "gov_us_co_upper_big_sandy_ground_water_management_district", "action_upper_big_sandy_groundwater_regulatory_inquiry"),
        "UPPER BLK SQUIRREL CRK GRD WD": ("groundwater_regulator", "gov_us_co_el_paso_upper_black_squirrel_creek_ground_water_management_district", "action_upper_black_squirrel_groundwater_regulatory_inquiry"),
    }

    def test_all_expected_raw_layer_values_are_classified(self):
        for layer_name, values in self.expected_raw_layer_values.items():
            for raw_name in values:
                with self.subTest(layer=layer_name, raw_name=raw_name):
                    features = [{"attributes": {"name": raw_name}}]
                    provider = resolver.normalize_provider(features)
                    overlays = resolver.classify_overlays(features)
                    classified = bool(provider) or bool(overlays)
                    self.assertTrue(classified, raw_name)
                    self.assertFalse(bool(provider) and bool(overlays), raw_name)

    def test_nonretail_overlay_values_never_normalize_as_provider(self):
        for raw_name, (expected_class, expected_object, expected_route) in self.expected_nonretail.items():
            with self.subTest(raw_name=raw_name):
                features = [{"attributes": {"name": raw_name}}]
                self.assertIsNone(resolver.normalize_provider(features))
                overlays = resolver.classify_overlays(features)
                self.assertEqual(len(overlays), 1)
                self.assertEqual(overlays[0]["resolver_class"], expected_class)
                self.assertEqual(overlays[0]["object_id"], expected_object)
                self.assertEqual(overlays[0]["action_route_id"], expected_route)

    def test_layer_inventory(self):
        for layer_name, item_id in resolver.COUNTY_LAYERS:
            service_url = resolver.arcgis_service_url(item_id)
            service_url = (service_url or "").rstrip("/")
            metadata = resolver.get_json(service_url, {"f": "json"})
            layers = metadata.get("layers") or []
            all_strings = set()
            targets = [layer.get("id") for layer in layers if layer.get("id") is not None]
            if not targets:
                targets = [None]
            for layer_id in targets:
                layer_url = service_url if layer_id is None else f"{service_url}/{layer_id}"
                data = resolver.get_json(layer_url + "/query", {
                    "f": "json",
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "false",
                })
                for feature in data.get("features") or []:
                    attrs = feature.get("attributes") or {}
                    for value in attrs.values():
                        if isinstance(value, str) and value.strip():
                            all_strings.add(value.strip())
            print({"layer_inventory": layer_name, "values": sorted(all_strings)})
            expected = self.expected_raw_layer_values.get(layer_name, set())
            self.assertTrue(expected.issubset(all_strings), {
                "layer": layer_name,
                "missing": sorted(expected - all_strings),
            })

    def _provider_centroid(self, provider_text):
        needle = provider_text.upper()
        for _layer_name, item_id in resolver.COUNTY_LAYERS:
            service_url = (resolver.arcgis_service_url(item_id) or "").rstrip("/")
            metadata = resolver.get_json(service_url, {"f": "json"})
            layers = metadata.get("layers") or []
            targets = [layer.get("id") for layer in layers if layer.get("id") is not None]
            if not targets:
                targets = [None]
            for layer_id in targets:
                layer_url = service_url if layer_id is None else f"{service_url}/{layer_id}"
                data = resolver.get_json(layer_url + "/query", {
                    "f": "json",
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "returnCentroid": "true",
                    "outSR": "4326",
                })
                for feature in data.get("features") or []:
                    attrs = feature.get("attributes") or {}
                    values = " | ".join(str(v) for v in attrs.values() if v is not None).upper()
                    if needle not in values:
                        continue

                    # Prefer ArcGIS centroid when it really intersects the feature.
                    centroid = feature.get("centroid") or {}
                    cx, cy = centroid.get("x"), centroid.get("y")
                    if cx is not None and cy is not None:
                        candidate = resolver.resolve("", cy, cx)
                        if (candidate.get("provider_id", "") or ""):
                            return cy, cx, values

                    # Some multipart/concave polygons have an ArcGIS centroid outside
                    # the actual service area. A polygon ring vertex is evidence-native
                    # and guaranteed to lie on the returned feature boundary.
                    geometry = feature.get("geometry") or {}
                    for ring in geometry.get("rings") or []:
                        for point in ring:
                            if isinstance(point, list) and len(point) >= 2:
                                x, y = point[0], point[1]
                                candidate = resolver.resolve("", y, x)
                                if (candidate.get("provider_id", "") or ""):
                                    return y, x, values
        self.fail(f"No intersecting provider point found for {provider_text}")

    def test_expansion_provider_polygon_controls(self):
        cases = [
            ("GARDEN VALLEY SWD", "gov_us_co_el_paso_garden_valley_water_sanitation_district", ""),
            ("FOREST VIEW ACRES WD", "gov_us_co_el_paso_forest_view_acres_water_district", "action_forest_view_acres_water_service_interruption"),
            ("PARK FOREST WD", "gov_us_co_el_paso_park_forest_water_district", ""),
            ("PIONEER LOOKOUT WD", "gov_us_co_el_paso_pioneer_lookout_water_district", "action_pioneer_lookout_water_service_issue"),
            ("RED ROCK VALLEY ESTATES WD", "gov_us_co_el_paso_red_rock_valley_estates_water_district", ""),
            ("ROCK CREEK MESA WD", "gov_us_co_el_paso_rock_creek_mesa_water_district", "action_rock_creek_mesa_water_service_interruption"),
            ("STRATMOOR HILLS WD", "gov_us_co_el_paso_stratmoor_hills_water_district", "action_stratmoor_hills_water_service_interruption"),
            ("TURKEY CANON RANCH WD", "gov_us_co_el_paso_turkey_canon_ranch_water_district", "action_turkey_canon_water_service_request"),
        ]
        failures = []
        for provider_text, expected_provider, expected_route in cases:
            with self.subTest(provider=provider_text):
                latitude, longitude, raw = self._provider_centroid(provider_text)
                result = resolver.resolve("", latitude, longitude)
                actual_provider = result.get("provider_id", "") or ""
                actual_route = result.get("action_route_id", "") or ""
                print({
                    "label": "EXPANSION_POLYGON_CENTROID",
                    "provider_text": provider_text,
                    "latitude": latitude,
                    "longitude": longitude,
                    "raw_provider": raw,
                    "expected_provider": expected_provider,
                    "actual_provider": actual_provider,
                    "expected_action_route": expected_route,
                    "actual_action_route": actual_route,
                    "resolver_status": result.get("resolver_status"),
                    "evidence_method": result.get("evidence_method"),
                    "diagnostics": result.get("diagnostics"),
                })
                if actual_provider != expected_provider or actual_route != expected_route:
                    failures.append((provider_text, expected_provider, actual_provider, expected_route, actual_route, result))
        self.assertFalse(failures, failures)

    def _overlay_intersecting_point(self, raw_name, expected_object_id):
        needle = raw_name.upper()
        for _layer_name, item_id in resolver.COUNTY_LAYERS:
            service_url = (resolver.arcgis_service_url(item_id) or "").rstrip("/")
            metadata = resolver.get_json(service_url, {"f": "json"})
            layers = metadata.get("layers") or []
            targets = [layer.get("id") for layer in layers if layer.get("id") is not None] or [None]
            for layer_id in targets:
                layer_url = service_url if layer_id is None else f"{service_url}/{layer_id}"
                data = resolver.get_json(layer_url + "/query", {
                    "f": "json",
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "true",
                    "returnCentroid": "true",
                    "outSR": "4326",
                })
                for feature in data.get("features") or []:
                    attrs = feature.get("attributes") or {}
                    values = " | ".join(str(v) for v in attrs.values() if v is not None).upper()
                    if needle not in values:
                        continue
                    points = []
                    centroid = feature.get("centroid") or {}
                    if centroid.get("x") is not None and centroid.get("y") is not None:
                        points.append((centroid["y"], centroid["x"]))
                    geometry = feature.get("geometry") or {}
                    for ring in geometry.get("rings") or []:
                        for point in ring:
                            if isinstance(point, list) and len(point) >= 2:
                                points.append((point[1], point[0]))
                                if len(points) >= 30:
                                    break
                        if len(points) >= 30:
                            break
                    for latitude, longitude in points:
                        result = resolver.resolve("", latitude, longitude)
                        overlays = json.loads(result.get("governance_overlays") or "[]")
                        if any(o.get("object_id") == expected_object_id for o in overlays):
                            return latitude, longitude, values, result
        self.fail(f"No live overlay control point found for {raw_name}")

    def test_nonretail_overlay_live_action_routes(self):
        for raw_name, (_expected_class, expected_object, expected_route) in self.expected_nonretail.items():
            with self.subTest(raw_name=raw_name):
                latitude, longitude, raw, result = self._overlay_intersecting_point(raw_name, expected_object)
                overlays = json.loads(result.get("governance_overlays") or "[]")
                match = next(o for o in overlays if o.get("object_id") == expected_object)
                print({
                    "label": "NONRETAIL_OVERLAY_LIVE",
                    "raw_name": raw_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "raw_overlay": raw,
                    "overlay_object_id": match.get("object_id"),
                    "overlay_action_route_id": match.get("action_route_id"),
                    "provider_id": result.get("provider_id", "") or "",
                    "provider_action_route_id": result.get("action_route_id", "") or "",
                })
                self.assertEqual(match.get("action_route_id"), expected_route)
                self.assertNotEqual(result.get("provider_id", "") or "", expected_object)
                self.assertNotEqual(result.get("action_route_id", "") or "", expected_route)

    def test_widefield_polygon_provider_and_route(self):
        latitude, longitude, raw = self._provider_centroid("WIDEFIELD SWD")
        result = resolver.resolve("", latitude, longitude)
        print({
            "label": "WIDEFIELD_POLYGON_CENTROID",
            "latitude": latitude,
            "longitude": longitude,
            "raw_provider": raw,
            "expected_provider": "gov_us_co_el_paso_widefield_wsd",
            "actual_provider": result.get("provider_id", "") or "",
            "expected_action_route": "action_widefield_water_service_interruption",
            "actual_action_route": result.get("action_route_id", "") or "",
            "resolver_status": result.get("resolver_status"),
            "evidence_method": result.get("evidence_method"),
            "diagnostics": result.get("diagnostics"),
        })
        self.assertEqual(result.get("provider_id", "") or "", "gov_us_co_el_paso_widefield_wsd")
        self.assertEqual(result.get("action_route_id", "") or "", "action_widefield_water_service_interruption")

    def test_live_provider_and_route_controls(self):
        failures = []
        for label, address, expected_provider, expected_route in self.cases:
            with self.subTest(label=label):
                result = resolver.resolve(address)
                actual_provider = result.get("provider_id", "") or ""
                actual_route = result.get("action_route_id", "") or ""
                print(
                    {
                        "label": label,
                        "address": address,
                        "expected_provider": expected_provider,
                        "actual_provider": actual_provider,
                        "expected_action_route": expected_route,
                        "actual_action_route": actual_route,
                        "resolver_status": result.get("resolver_status"),
                        "geocode_status": result.get("geocode_status"),
                        "matched_address": result.get("matched_address"),
                        "evidence_method": result.get("evidence_method"),
                        "diagnostics": result.get("diagnostics"),
                    }
                )
                if actual_provider != expected_provider or actual_route != expected_route:
                    failures.append(
                        (label, expected_provider, actual_provider, expected_route, actual_route, result)
                    )
        self.assertFalse(failures, failures)


    def test_additional_location_gated_city_service_routes(self):
        spatial = resolver.resolve("111 S Cascade Ave, Colorado Springs, CO 80903")
        cases = [
            (
                "The traffic signal is malfunctioning.",
                "transportation",
                "traffic_signal_or_sign_issue",
                "action_cos_traffic_signal_sign_report",
            ),
            (
                "There is a clogged storm drain.",
                "stormwater",
                "clogged_storm_drain_or_drainage_maintenance",
                "action_cos_storm_drain_maintenance",
            ),
            (
                "The streetlight is out.",
                "transportation",
                "streetlight_outage_or_damage",
                "action_cos_streetlight_maintenance",
            ),
        ]
        for issue, expected_domain, expected_type, expected_route in cases:
            with self.subTest(issue=issue):
                result = resolver.apply_issue_route(spatial, issue)
                self.assertEqual(result["issue_domain"], expected_domain)
                self.assertEqual(result["issue_type"], expected_type)
                self.assertEqual(result["issue_classifier_status"], "ROUTED")
                self.assertEqual(result["issue_route_source"], "institution")
                self.assertEqual(result["issue_route_id"], expected_route)

        missing = {"resolver_status": "UNRESOLVED", "geocode_status": "MISSING_INPUT", "governance_overlays": ""}
        for issue, _domain, _type, _route in cases:
            with self.subTest(missing_location=issue):
                result = resolver.apply_issue_route(missing, issue)
                self.assertEqual(result["issue_classifier_status"], "NEEDS_LOCATION")
                self.assertEqual(result["issue_route_id"], "")

        lat, lon, _raw = self._provider_centroid("WOODMOOR SWD")
        outside = resolver.resolve("", lat, lon)
        for issue, _domain, _type, _route in cases:
            with self.subTest(outside_city=issue):
                result = resolver.apply_issue_route(outside, issue)
                self.assertEqual(result["issue_classifier_status"], "NO_APPLICABLE_ROUTE")
                self.assertEqual(result["issue_route_id"], "")

    def test_pothole_location_gated_routing(self):
        # In-city address routes to City Public Works pothole intake.
        spatial = resolver.resolve("111 S Cascade Ave, Colorado Springs, CO 80903")
        result = resolver.apply_issue_route(spatial, "There is a pothole in the road.")
        self.assertEqual(result["issue_domain"], "transportation")
        self.assertEqual(result["issue_type"], "pothole_or_street_surface_defect")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_source"], "institution")
        self.assertEqual(result["issue_route_id"], "action_cos_pothole_report")

        # Missing location fails closed.
        result = resolver.apply_issue_route(
            {"resolver_status": "UNRESOLVED", "geocode_status": "MISSING_INPUT", "governance_overlays": ""},
            "There is a pothole in the road.",
        )
        self.assertEqual(result["issue_classifier_status"], "NEEDS_LOCATION")
        self.assertEqual(result["issue_route_id"], "")

        # A point in the Woodmoor service area is outside the Colorado Springs place boundary.
        lat, lon, _raw = self._provider_centroid("WOODMOOR SWD")
        spatial = resolver.resolve("", lat, lon)
        result = resolver.apply_issue_route(spatial, "There is a pothole in the road.")
        self.assertEqual(result["issue_classifier_status"], "NO_APPLICABLE_ROUTE")
        self.assertEqual(result["issue_route_id"], "")

    def test_cross_domain_institution_routes_without_location(self):
        unresolved = {"resolver_status": "UNRESOLVED", "geocode_status": "MISSING_INPUT", "governance_overlays": ""}

        result = resolver.apply_issue_route(
            unresolved,
            "I need an ADA accommodation for a Colorado Springs city program.",
        )
        self.assertEqual(result["issue_domain"], "accessibility")
        self.assertEqual(result["issue_type"], "public_program_accessibility_barrier")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_source"], "institution")
        self.assertEqual(result["issue_route_id"], "action_cos_accessibility_public_program")

        result = resolver.apply_issue_route(
            unresolved,
            "I want to file a CORA request for Colorado Springs city records.",
        )
        self.assertEqual(result["issue_domain"], "public_records")
        self.assertEqual(result["issue_type"], "city_public_record_request")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_source"], "institution")
        self.assertEqual(result["issue_route_id"], "action_cos_public_records_general")

    def test_cross_domain_needs_institution(self):
        unresolved = {"resolver_status": "UNRESOLVED", "geocode_status": "MISSING_INPUT", "governance_overlays": ""}

        result = resolver.apply_issue_route(unresolved, "I need public records.")
        self.assertEqual(result["issue_domain"], "public_records")
        self.assertEqual(result["issue_type"], "city_public_record_request")
        self.assertEqual(result["issue_classifier_status"], "NEEDS_INSTITUTION")
        self.assertEqual(result["issue_route_id"], "")

        result = resolver.apply_issue_route(unresolved, "I need an ADA accommodation.")
        self.assertEqual(result["issue_domain"], "accessibility")
        self.assertEqual(result["issue_classifier_status"], "NEEDS_INSTITUTION")
        self.assertEqual(result["issue_route_id"], "")

    def test_issue_classifier_plain_language_routes(self):
        # Retail service problem → direct provider Action Route.
        result = resolver.apply_issue_route(
            resolver.resolve("111 S Cascade Ave, Colorado Springs, CO 80903"),
            "My water is out and I have no water.",
        )
        self.assertEqual(result["issue_type"], "water_service_interruption")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_source"], "provider")
        self.assertEqual(result["issue_route_id"], "action_cos_water_service_interruption")

        # Groundwater question → groundwater-regulator overlay, not retail provider.
        lat, lon, _raw, spatial = self._overlay_intersecting_point(
            "UPPER BLK SQUIRREL CRK GRD WD",
            "gov_us_co_el_paso_upper_black_squirrel_creek_ground_water_management_district",
        )
        result = resolver.apply_issue_route(spatial, "I have a well permit and groundwater rules question.")
        self.assertEqual(result["issue_type"], "groundwater_regulatory_question")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_source"], "governance_overlay")
        self.assertEqual(result["issue_route_id"], "action_upper_black_squirrel_groundwater_regulatory_inquiry")

        # Augmentation → UAWCD overlay route.
        lat, lon, _raw, spatial = self._overlay_intersecting_point(
            "UPPER ARKANSAS WCD",
            "gov_us_co_upper_arkansas_water_conservancy_district",
        )
        result = resolver.apply_issue_route(spatial, "I need augmentation water for my well.")
        self.assertEqual(result["issue_type"], "augmentation_water_need")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_id"], "action_uawcd_augmentation_application")

        # Project Water → SECWCD overlay route, even where CSU is the retail provider.
        lat, lon, _raw, spatial = self._overlay_intersecting_point(
            "SOUTHEASTERN COLORADO WATER CONSERVANCY",
            "gov_us_co_southeastern_colorado_water_conservancy_district",
        )
        result = resolver.apply_issue_route(spatial, "We want to apply for Fryingpan-Arkansas Project Water allocation.")
        self.assertEqual(result["issue_type"], "project_water_allocation")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_id"], "action_secwcd_project_water_allocation")
        self.assertNotEqual(result["issue_route_id"], result.get("action_route_id", ""))

        # Cheyenne Creek governance → specialized overlay route, not CSU route.
        lat, lon, _raw, spatial = self._overlay_intersecting_point(
            "CHEYENNE CREEK MD PARK & WATER",
            "gov_us_co_el_paso_cheyenne_creek_metropolitan_district",
        )
        result = resolver.apply_issue_route(spatial, "I have a Cheyenne Creek streamflow and water-rights question.")
        self.assertEqual(result["issue_type"], "cheyenne_creek_governance")
        self.assertEqual(result["issue_classifier_status"], "ROUTED")
        self.assertEqual(result["issue_route_id"], "action_cheyenne_creek_streamflow_governance_inquiry")

    def test_issue_classifier_fail_closed_states(self):
        # A direct provider can resolve while its process route remains held.
        lat, lon, _raw = self._provider_centroid("GARDEN VALLEY SWD")
        spatial = resolver.resolve("", lat, lon)
        result = resolver.apply_issue_route(spatial, "My water is out.")
        self.assertEqual(result["provider_id"], "gov_us_co_el_paso_garden_valley_water_sanitation_district")
        self.assertEqual(result["issue_classifier_status"], "PROCESS_BLOCKED")
        self.assertEqual(result["issue_route_id"], "")

        # Recognized issue with no location asks for location rather than guessing.
        result = resolver.apply_issue_route(
            {"resolver_status": "UNRESOLVED", "geocode_status": "MISSING_INPUT"},
            "My water is out.",
        )
        self.assertEqual(result["issue_classifier_status"], "NEEDS_LOCATION")

        # Unsupported language stays unsupported.
        result = resolver.apply_issue_route(
            resolver.resolve("111 S Cascade Ave, Colorado Springs, CO 80903"),
            "I need help with something unrelated.",
        )
        self.assertEqual(result["issue_classifier_status"], "UNSUPPORTED")
        self.assertEqual(result["issue_route_id"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
