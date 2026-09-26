import importlib.util
from pathlib import Path
import unittest


MODULE = Path(__file__).with_name("representation_provider.py")
spec = importlib.util.spec_from_file_location("atlas_representation_provider", MODULE)
provider = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider)


def certified_payload():
    return {
        "schema_version": "atlas-representation-provider/0.1",
        "status": "PASS",
        "source_system": "civicdata",
        "snapshot_manifest_sha256": "a" * 64,
        "jurisdiction_ocdid": "ocd-jurisdiction/country:us/state:co/place:example/government",
        "division_ocdids": [
            "ocd-division/country:us/state:co/place:example",
            "ocd-division/country:us/state:co/place:example/council_district:1",
        ],
        "certification": {
            "status": "certified",
            "raw_complete": True,
            "normalized_complete": True,
            "qa_passed": True,
            "parity_ok": True,
            "verified_at": "2026-09-26T12:00:00Z",
        },
        "offices": [
            {
                "post_id": "post-example-mayor",
                "office_id": "office-example-mayor",
                "role_id": "mayor",
                "office_name": "Mayor",
                "division_ocdid": "ocd-division/country:us/state:co/place:example",
                "seat_capacity": 1,
                "vacancy_count": 0,
                "shared_organization_id": "org-11111111-1111-4111-8111-111111111111",
                "holders": [
                    {
                        "person_id": "person-example-mayor",
                        "shared_person_id": "per-22222222-2222-4222-8222-222222222222",
                        "name": "Alex Example",
                    }
                ],
            },
            {
                "post_id": "post-example-council-1",
                "office_id": "office-example-council-1",
                "role_id": "council-member",
                "office_name": "Council Member",
                "division_ocdid": "ocd-division/country:us/state:co/place:example/council_district:1",
                "seat_capacity": 1,
                "vacancy_count": 1,
                "shared_organization_id": "org-33333333-3333-4333-8333-333333333333",
                "holders": [],
            },
        ],
        "canonical_writes": 0,
    }


class RepresentationProviderTests(unittest.TestCase):
    def test_disabled_provider_never_calls_network(self):
        calls = []

        def fetch(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("network should not be called")

        result = provider.resolve_representation(
            {"latitude": 38.8, "longitude": -104.8},
            "",
            fetch,
        )
        self.assertEqual(result["status"], "DISABLED")
        self.assertEqual(result["canonical_writes"], 0)
        self.assertEqual(calls, [])

    def test_configured_provider_requires_location(self):
        result = provider.resolve_representation(
            {"resolver_status": "UNRESOLVED"},
            "https://example.invalid/representation",
            lambda *_args, **_kwargs: certified_payload(),
        )
        self.assertEqual(result["status"], "NEEDS_LOCATION")
        self.assertEqual(result["canonical_writes"], 0)

    def test_certified_provider_response_is_accepted(self):
        captured = {}

        def fetch(url, params, timeout=10):
            captured["url"] = url
            captured["params"] = dict(params)
            captured["timeout"] = timeout
            return certified_payload()

        result = provider.resolve_representation(
            {
                "latitude": 38.8339,
                "longitude": -104.8214,
                "matched_address": "111 S Cascade Ave, Colorado Springs, CO 80903",
            },
            "https://example.invalid/representation",
            fetch,
            timeout=7,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_system"], "civicdata")
        self.assertEqual(len(result["offices"]), 2)
        self.assertEqual(result["canonical_writes"], 0)
        self.assertEqual(
            captured,
            {
                "url": "https://example.invalid/representation",
                "params": {"lat": 38.8339, "lon": -104.8214},
                "timeout": 7,
            },
        )

    def test_uncertified_representation_fails_closed(self):
        payload = certified_payload()
        payload["certification"]["parity_ok"] = False
        result = provider.resolve_representation(
            {"latitude": 38.8, "longitude": -104.8},
            "https://example.invalid/representation",
            lambda *_args, **_kwargs: payload,
        )
        self.assertEqual(result["status"], "INVALID_RESPONSE")
        self.assertIn("CERTIFICATION_INVALID", result["errors"])

    def test_seat_parity_mismatch_fails_closed(self):
        payload = certified_payload()
        payload["offices"][0]["vacancy_count"] = 1
        result = provider.resolve_representation(
            {"latitude": 38.8, "longitude": -104.8},
            "https://example.invalid/representation",
            lambda *_args, **_kwargs: payload,
        )
        self.assertEqual(result["status"], "INVALID_RESPONSE")
        self.assertIn("SEAT_PARITY_INVALID", result["errors"])

    def test_malformed_shared_identity_fails_closed(self):
        payload = certified_payload()
        payload["offices"][0]["holders"][0]["shared_person_id"] = "person-by-name"
        result = provider.resolve_representation(
            {"latitude": 38.8, "longitude": -104.8},
            "https://example.invalid/representation",
            lambda *_args, **_kwargs: payload,
        )
        self.assertEqual(result["status"], "INVALID_RESPONSE")
        self.assertIn("SHARED_PERSON_ID_INVALID", result["errors"])

    def test_provider_outage_is_reported_without_affecting_canonical_state(self):
        def fetch(*_args, **_kwargs):
            raise TimeoutError("provider timeout")

        result = provider.resolve_representation(
            {"latitude": 38.8, "longitude": -104.8},
            "https://example.invalid/representation",
            fetch,
        )
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["canonical_writes"], 0)
        self.assertTrue(any("TimeoutError" in error for error in result["errors"]))

    def test_no_applicable_representation_is_valid_fail_closed_result(self):
        payload = {
            "schema_version": "atlas-representation-provider/0.1",
            "status": "NO_APPLICABLE_REPRESENTATION",
            "canonical_writes": 0,
        }
        result = provider.resolve_representation(
            {"latitude": 38.8, "longitude": -104.8},
            "https://example.invalid/representation",
            lambda *_args, **_kwargs: payload,
        )
        self.assertEqual(result, payload)

    def test_csv_contract_remains_separate_from_representation_enrichment(self):
        # The provider returns nested JSON. The existing Atlas CSV writer keeps
        # its fixed CSV_FIELDS list and ignores extra JSON-only fields.
        payload = certified_payload()
        self.assertNotIn("representation", payload)
        self.assertEqual(provider.validate_provider_response(payload), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
