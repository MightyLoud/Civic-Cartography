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
            "FAIL_CLOSED",
            "2586 Soma View, Colorado Springs, CO 80922",
            "",
            "",
        ),
    ]

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
