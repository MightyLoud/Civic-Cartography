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
                    "returnGeometry": "false",
                    "returnCentroid": "true",
                    "outSR": "4326",
                })
                for feature in data.get("features") or []:
                    attrs = feature.get("attributes") or {}
                    values = " | ".join(str(v) for v in attrs.values() if v is not None).upper()
                    if needle in values:
                        centroid = feature.get("centroid") or {}
                        if centroid.get("x") is not None and centroid.get("y") is not None:
                            return centroid["y"], centroid["x"], values
        self.fail(f"No centroid found for {provider_text}")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
