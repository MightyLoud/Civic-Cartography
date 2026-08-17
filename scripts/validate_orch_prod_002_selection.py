#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

EXPECTED = {
    "OR-PB04-001": ("41007", "Clatsop County", "clatsop", "OR-PB04-A", []),
    "OR-PB04-002": ("41009", "Columbia County", "columbia", "OR-PB04-A", []),
    "OR-PB04-003": ("41011", "Coos County", "coos", "OR-PB04-B", ["OR-PB04-001"]),
    "OR-PB04-004": ("41013", "Crook County", "crook", "OR-PB04-B", ["OR-PB04-002"]),
    "OR-PB04-005": ("41015", "Curry County", "curry", "OR-PB04-C", ["OR-PB04-003", "OR-PB04-004"]),
}
OCD_PREFIX = "ocd-division/country:us/state:or/county:"


def fail(msg: str) -> None:
    raise SystemExit(f"SELECTION FAIL: {msg}")


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("batch_id") != "OR-PB04": fail("batch_id")
    if data.get("capacity") != 2: fail("capacity must be 2")
    targets = data.get("targets", [])
    if len(targets) != 5 or data.get("target_count") != 5: fail("target count must be 5")

    ids = [t.get("target_id") for t in targets]
    if len(set(ids)) != 5 or set(ids) != set(EXPECTED): fail("target IDs")
    if sorted(t.get("sequence") for t in targets) != [1,2,3,4,5]: fail("sequence")

    waves = Counter()
    seen = set()
    for t in sorted(targets, key=lambda x: x["sequence"]):
        tid = t["target_id"]
        geoid, name, slug, wave, deps = EXPECTED[tid]
        if t.get("census_geoid") != geoid: fail(f"{tid} GEOID")
        if t.get("state_fips") != "41" or not re.fullmatch(r"41\d{3}", geoid): fail(f"{tid} Oregon GEOID")
        if t.get("county_fips") != geoid[-3:]: fail(f"{tid} county FIPS")
        if t.get("display_name") != name: fail(f"{tid} name")
        if t.get("maintained_ocdid") != OCD_PREFIX + slug: fail(f"{tid} OCDID")
        if t.get("expected_classification") != "government": fail(f"{tid} classification")
        if t.get("wave") != wave: fail(f"{tid} wave")
        if t.get("dependencies") != deps: fail(f"{tid} dependencies")
        if any(dep not in seen for dep in deps): fail(f"{tid} dependency not prior")
        nesting = t.get("nesting", {})
        if not nesting.get("sldu_fips") or not nesting.get("sldl_fips"): fail(f"{tid} nesting")
        waves[wave] += 1
        seen.add(tid)

    if waves != Counter({"OR-PB04-A": 2, "OR-PB04-B": 2, "OR-PB04-C": 1}): fail("wave shape")
    if any(v > data["capacity"] for v in waves.values()): fail("wave exceeds capacity")
    print("ORCH-PROD-002 selection PASS: 5 targets; wave shape 2/2/1; capacity=2; DAG valid")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_orch_prod_002_selection.py <selection-crosswalk.json>")
    main(sys.argv[1])
