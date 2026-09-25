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
        ),
        (
            "DONALA",
            "13631 Shepard Hts, Colorado Springs, CO 80921",
            "gov_us_co_el_paso_donala_wsd",
        ),
        (
            "SECURITY",
            "4613 Dancing Light Way, Colorado Springs, CO 80911",
            "gov_us_co_el_paso_security_wsd",
        ),
        (
            "FAIL_CLOSED",
            "2586 Soma View, Colorado Springs, CO 80922",
            "",
        ),
    ]

    def test_live_provider_controls(self):
        failures = []
        for label, address, expected in self.cases:
            with self.subTest(label=label):
                result = resolver.resolve(address)
                actual = result.get("provider_id", "") or ""
                print(
                    {
                        "label": label,
                        "address": address,
                        "expected": expected,
                        "actual": actual,
                        "resolver_status": result.get("resolver_status"),
                        "geocode_status": result.get("geocode_status"),
                        "matched_address": result.get("matched_address"),
                        "evidence_method": result.get("evidence_method"),
                        "diagnostics": result.get("diagnostics"),
                    }
                )
                if actual != expected:
                    failures.append((label, expected, actual, result))
        self.assertFalse(failures, failures)


if __name__ == "__main__":
    unittest.main(verbosity=2)
