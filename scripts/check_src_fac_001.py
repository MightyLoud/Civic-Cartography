#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

FIXTURE = pathlib.Path("tests/fixtures/src_fac_001_known_good_sources.json")
SCHEMA = pathlib.Path("schemas/source-discovery.schema.json")
REQUIRED_STATES = {"AK", "HI", "CO", "OR", "NM", "WA", "VA"}
GOVERNED_ADAPTERS = {
    "ADP-WB027-001", "ADP-WB027-002", "ADP-WB027-003", "ADP-WB027-016",
    "ADP-WB027-020", "ADP-WB027-024", "ADP-WB027-029",
}
OFFICIAL_SUFFIXES = (
    "elections.alaska.gov", "elections.hawaii.gov", "coloradosos.gov",
    "sos.state.co.us", "sos.oregon.gov", "sos.nm.gov", "sos.wa.gov",
    "elections.virginia.gov",
)


def canonical_hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate(data, schema):
    errors = [
        f"schema: {error.message}"
        for error in Draft202012Validator(schema).iter_errors(data)
    ]
    cases = data.get("cases", [])
    if len(cases) != 10:
        errors.append(f"expected 10 cases, got {len(cases)}")
    states = {case.get("state") for case in cases}
    if not REQUIRED_STATES.issubset(states):
        errors.append(f"missing required states: {sorted(REQUIRED_STATES - states)}")

    ids = set()
    for case in cases:
        cid = case.get("case_id")
        if cid in ids:
            errors.append(f"duplicate case_id {cid}")
        ids.add(cid)
        disposition = case.get("disposition")
        if disposition not in {"READY", "REVIEW", "BLOCKED"}:
            errors.append(f"{cid}: bad disposition")
        for src in case.get("candidate_sources", []):
            host = (urlparse(src.get("url", "")).hostname or "").lower()
            if not any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_SUFFIXES):
                errors.append(f"{cid}: non-official host {host}")
            if src.get("authority_level") != "OFFICIAL":
                errors.append(f"{cid}: authority not OFFICIAL")
            if src.get("status") not in {"ACTIVE", "STALE", "BROKEN"}:
                errors.append(f"{cid}: bad source status")

            adapter_id = src.get("adapter_id")
            match = src.get("adapter_match")
            if match not in {"EXACT", "LIKELY", "NONE"}:
                errors.append(f"{cid}: bad adapter match")
            elif match == "NONE":
                if adapter_id is not None:
                    errors.append(f"{cid}: NONE match must not claim an adapter")
                if disposition != "BLOCKED":
                    errors.append(f"{cid}: NONE match must fail closed to BLOCKED")
            elif adapter_id not in GOVERNED_ADAPTERS:
                errors.append(f"{cid}: ungoverned adapter {adapter_id}")

            if match == "EXACT" and src.get("schema_fingerprint") in {
                "GUIDANCE_ONLY", "DIRECTORY", "LOCAL_ROUTING", "UNFINGERPRINTED_OFFICIAL_HTML"
            }:
                errors.append(f"{cid}: unsupported EXACT match")
            if match == "LIKELY" and disposition == "READY":
                errors.append(f"{cid}: LIKELY match cannot be READY")
    return errors


def main():
    data = json.loads(FIXTURE.read_text())
    schema = json.loads(SCHEMA.read_text())
    first_hash = canonical_hash(data)
    second_hash = canonical_hash(json.loads(FIXTURE.read_text()))
    errors = validate(data, schema)
    if first_hash != second_hash:
        errors.append("determinism hash mismatch")

    states = sorted({case.get("state") for case in data.get("cases", [])})
    print(f"cases={len(data.get('cases', []))}")
    print(f"states={','.join(states)}")
    print(f"canonical_sha256={first_hash}")
    print(f"deterministic={first_hash == second_hash}")
    if errors:
        print("\n".join("FAIL: " + error for error in errors))
        return 1
    print("SRC-FAC-001 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
