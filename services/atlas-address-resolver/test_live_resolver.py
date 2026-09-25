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
            "WIDEFIELD",
            "8495 Fontaine Blvd, Colorado Springs, CO 80925",
            "gov_us_co_el_paso_widefield_wsd",
            "action_widefield_water_service_interruption",
        ),
        (
            "WOODMOOR",
            "1845 Woodmoor Drive, Monument, CO 80132",
            "gov_us_co_el_paso_woodmoor_water",
            "action_woodmoor_water_service_interruption",
        ),
        (
            "ACADEMY",
            "1755 Spring Valley Drive, Colorado Springs, CO 80921",
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
