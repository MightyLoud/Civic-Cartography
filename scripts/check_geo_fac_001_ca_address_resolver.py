#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evidence/geo-fac-001/ca-address-resolver-smoke.json"

EXPECTED = {
    "addr-ca-amador-city-cityhall": ("jurisdiction-ca-amador-city", "division-ca-amador-city-citywide"),
    "addr-ca-apple-valley-townhall": ("jurisdiction-ca-apple-valley", "division-ca-apple-valley-citywide"),
    "addr-ca-berkeley-cityhall": ("jurisdiction-ca-berkeley", "division-ca-berkeley-citywide"),
    "addr-ca-irvine-civiccenter": ("jurisdiction-ca-irvine", "division-ca-irvine-citywide"),
    "addr-ca-belmont-cityhall": ("jurisdiction-ca-belmont", "division-ca-belmont-citywide"),
    "addr-ca-adelanto-cityhall": ("jurisdiction-ca-adelanto", "division-ca-adelanto-citywide"),
    "addr-ca-agoura-hills-cityhall": ("jurisdiction-ca-agoura-hills", "division-ca-agoura-hills-citywide"),
    "addr-ca-alameda-cityhall": ("jurisdiction-ca-alameda", "division-ca-alameda-citywide"),
    "addr-ca-albany-cityhall": ("jurisdiction-ca-albany", "division-ca-albany-citywide"),
    "addr-ca-alhambra-cityhall": ("jurisdiction-ca-alhambra", "division-ca-alhambra-citywide"),
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def canonical_hash(obj: object) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def row_source_hash(row: dict) -> str:
    payload = {
        "address_input": row["address_input"],
        "normalized_address": row["normalized_address"],
        "jurisdiction_id": row["jurisdiction_id"],
        "division_id": row["division_id"],
        "boundary_source_id": row["boundary_source_id"],
    }
    return canonical_hash(payload)


def validate(data: dict) -> str:
    if data.get("contract_version") != "1.0":
        fail("unexpected contract_version")
    records = data.get("records")
    if not isinstance(records, list) or len(records) != 10:
        fail("expected exactly 10 records")

    seen = set()
    for row in records:
        test_id = row.get("test_id")
        if test_id not in EXPECTED:
            fail(f"unexpected test_id: {test_id}")
        if test_id in seen:
            fail(f"duplicate test_id: {test_id}")
        seen.add(test_id)

        expected_jurisdiction, expected_division = EXPECTED[test_id]
        if row.get("jurisdiction_id") != expected_jurisdiction:
            fail(f"jurisdiction mismatch: {test_id}")
        if row.get("division_id") != expected_division:
            fail(f"division mismatch: {test_id}")
        if row.get("status") != "PASS":
            fail(f"unexpected status: {test_id}")

        source_id = row.get("boundary_source_id")
        if not source_id or source_id not in row.get("evidence", []):
            fail(f"boundary source missing from evidence: {test_id}")

        geocode = row.get("geocode", {})
        if geocode.get("provider") != "FIXTURE":
            fail(f"smoke must not masquerade as live geocoding: {test_id}")
        if geocode.get("lat") is not None or geocode.get("lon") is not None:
            fail(f"GEO-FAC-001 fixture must not invent coordinates: {test_id}")

        local_layers = row.get("local_layers", {})
        if local_layers.get("resolved"):
            fail(f"unsupported local-layer resolution: {test_id}")
        if "city_council_district" not in local_layers.get("unresolved", []):
            fail(f"missing explicit unresolved local district: {test_id}")

        digest = row_source_hash(row)
        if digest != row.get("raw_sha256"):
            fail(f"source hash mismatch: {test_id}")

    if seen != set(EXPECTED):
        fail("fixture coverage mismatch")
    return canonical_hash(data)


def main() -> None:
    first = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hash_one = validate(first)
    second = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hash_two = validate(second)
    if hash_one != hash_two:
        fail("deterministic rerun hash mismatch")
    print(f"GEO-FAC-001 PASS: 10/10 canonical address controls; deterministic_sha256={hash_one}")


if __name__ == "__main__":
    main()
