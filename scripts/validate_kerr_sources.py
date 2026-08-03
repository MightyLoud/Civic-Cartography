#!/usr/bin/env python3
"""Validate Kerr County roster, succession, scope, and live GIS contracts."""
from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path("data/raw/kerr-county")
ROSTER = ROOT / "current-elected-offices.csv"
TRANSITION = ROOT / "district-clerk-transition.csv"
NON_SCOPE = ROOT / "non-scope-offices.csv"
MANIFEST = ROOT / "source-manifest.csv"
CONTRACT = ROOT / "gis-source-contract.json"

SERVICE = (
    "https://services1.arcgis.com/Ijqs2ihddUy84otW/ArcGIS/rest/services/"
    "Kerr_County_Commissioner_Precincts_2022/FeatureServer"
)
LAYER = f"{SERVICE}/0"
ITEM_ID = "de7c8e02045a4981a752998bb6406538"
FIELD = "precinct"
HEADERS = {"User-Agent": "Civic-Cartography-validator/1.0"}

EXPECTED_ROSTER = {
    "County Judge": "Rob Kelly",
    "County Commissioner Precinct 1": "Tom Jones",
    "County Commissioner Precinct 2": "Rich Paces",
    "County Commissioner Precinct 3": "Jeff Holt",
    "County Commissioner Precinct 4": "Don Harris",
    "Sheriff": "Larry L. Leitha Jr.",
    "County Clerk": "Nadene Alford",
    "District Clerk": "Eunavae Baublit Tonroy",
    "Tax Assessor-Collector": "Bob Reeves",
    "County Treasurer": "Tracy Soldan",
}
REQUIRED_SOURCES = {
    "kerr-commissioners-court",
    "kerr-elections-current-officeholders",
    "kerr-sheriff-home",
    "kerr-sheriff-biography",
    "kerr-county-clerk",
    "kerr-county-clerk-2024-appointment-expiry",
    "kerr-district-clerk-current",
    "kerr-district-clerk-appointment",
    "kerr-bail-bond-board",
    "texas-government-code-51-301",
    "texas-sos-2026-office-qualifications",
    "kerr-tax-assessor",
    "kerr-treasurer",
    "kerr-treasurer-history",
    "kerr-county-surveyor",
    "kerr-arcgis-service-item",
    "kerr-arcgis-precinct-layer",
    "census-kerr-county",
}
LIVE_PAGE_CONTRACTS = {
    "https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-commissioners-court": (
        "Rob Kelly", "Tom Jones", "Rich Paces", "Jeff Holt", "Don Harris"
    ),
    "https://www.kerrcountysheriff.com/about-the-kerr-county-sheriff-s-office": (
        "Larry L. Leitha", "elected in 2020"
    ),
    "https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-clerk": (
        "Nadene Alford", "County Clerk"
    ),
    "https://kerrcountytx.gov/blog/nadene-alford-appointed-by-court-as-new-kerr-county-clerk": (
        "Nadene Alford", "appointed"
    ),
    "https://www.kerrcountytx.gov/kerr-county-all-departments/clerk-of-the-district-courts-of-kerr-county": (
        "Eunavae Baublit", "District Clerk"
    ),
    "https://kerrcountytx.gov/blog/district-clerk-to-retire-march-31-appointment-made-to-serve-out-term": (
        "Dawn Lantz", "Eunavae Baublit Tonroy", "M. Patrick Maguire", "Albert D. Pattillo III"
    ),
    "https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-tax-assessor-collector": (
        "Bob Reeves", "Tax Assessor"
    ),
    "https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-treasurer": (
        "Tracy Soldan", "four years"
    ),
    "https://kerrcountytx.gov/kerr-county-all-departments/kerr-county-surveyor": (
        "Lee Voelkel", "County Surveyor"
    ),
}


def fetch_json(url: str, attempts: int = 5) -> dict[str, Any]:
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=45) as response:
                value = json.load(response)
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object from {url}")
            return value
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(attempt * 4)
    raise AssertionError("unreachable")


def fetch_optional_html(url: str) -> str | None:
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return html.unescape(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(f"Optional page unavailable: {url}: {exc}")
        return None


def searchable(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_committed_evidence() -> None:
    roster = read_csv(ROSTER)
    actual = {row["office_name"]: row["officeholder"] for row in roster}
    if len(roster) != 10 or actual != EXPECTED_ROSTER:
        raise SystemExit(f"Committed Kerr roster changed: {actual!r}")
    if len(set(actual.values())) != 10:
        raise SystemExit("Kerr roster contains duplicate current holders.")
    methods = [row["selection_method"] for row in roster]
    if methods.count("election") != 9 or methods.count("judicial_appointment") != 1:
        raise SystemExit(f"Unexpected current-entry methods: {methods!r}")
    appointed = next(row for row in roster if row["selection_method"] == "judicial_appointment")
    if appointed["office_name"] != "District Clerk" or "Dawn Lantz" not in appointed["notes"]:
        raise SystemExit("District Clerk judicial succession is not preserved in the roster.")

    transitions = read_csv(TRANSITION)
    if len(transitions) != 1:
        raise SystemExit(f"Expected one transition row, found {len(transitions)}")
    transition = transitions[0]
    expected_transition = {
        "office_name": "District Clerk",
        "office_status": "elected_office",
        "current_officeholder": "Eunavae Baublit Tonroy",
        "selection_method": "judicial_appointment",
        "predecessor": "Dawn Lantz",
        "predecessor_last_day": "2026-03-31",
        "appointment_announced_date": "2026-03-16",
        "current_service_start": "2026-04-01",
    }
    for key, value in expected_transition.items():
        if transition.get(key) != value:
            raise SystemExit(f"Transition field changed: {key}={transition.get(key)!r}")
    for judge in ("M. Patrick Maguire", "Albert D. Pattillo III"):
        if judge not in transition["appointing_authorities"]:
            raise SystemExit(f"Transition lost appointing judge: {judge}")

    non_scope = read_csv(NON_SCOPE)
    surveyor = next((row for row in non_scope if row["office_name"] == "County Surveyor"), None)
    if not surveyor or surveyor["current_officeholder"] != "Lee C. Voelkel":
        raise SystemExit("County Surveyor non-scope evidence is missing.")
    if "County Surveyor" in actual:
        raise SystemExit("County Surveyor leaked into the bounded release.")

    manifest = read_csv(MANIFEST)
    by_id = {row["source_id"]: row for row in manifest}
    if len(manifest) != 18 or set(by_id) != REQUIRED_SOURCES:
        raise SystemExit(f"Source manifest changed: {set(by_id)!r}")
    markers = {
        "kerr-elections-current-officeholders": "Dawn Lantz",
        "kerr-county-clerk-2024-appointment-expiry": "December 31, 2024",
        "kerr-district-clerk-appointment": "joint selection",
        "kerr-county-surveyor": "outside the bounded ten-office release",
        "kerr-arcgis-precinct-layer": "Court Order 39047",
    }
    for source_id, marker in markers.items():
        if marker not in by_id[source_id]["use"]:
            raise SystemExit(f"Manifest lost {marker!r} in {source_id}")

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected_contract = {
        "service_item_id": ITEM_ID,
        "operational_layer_id": 0,
        "operational_layer_url": LAYER,
        "geometry_type": "esriGeometryPolygon",
        "district_field": FIELD,
        "district_values": ["1", "2", "3", "4"],
        "resolved_from_county_elections_page": True,
    }
    for key, value in expected_contract.items():
        if contract.get(key) != value:
            raise SystemExit(f"GIS contract changed: {key}={contract.get(key)!r}")
    rows = contract.get("source_rows", [])
    if len(rows) != 4 or {str(row.get(FIELD)) for row in rows} != {"1", "2", "3", "4"}:
        raise SystemExit(f"GIS contract lost precinct rows: {rows!r}")
    if {str(row.get("order_num")) for row in rows} != {"39047"}:
        raise SystemExit("GIS contract lost Court Order 39047.")
    if {row.get("order_date") for row in rows} != {1635919200000}:
        raise SystemExit("GIS contract order date changed.")
    if {row.get("effective_date") for row in rows} != {1641016800000}:
        raise SystemExit("GIS contract effective date changed.")


def validate_optional_pages() -> None:
    accessible = 0
    for url, markers in LIVE_PAGE_CONTRACTS.items():
        raw = fetch_optional_html(url)
        if raw is None:
            continue
        page = searchable(raw)
        missing = [marker for marker in markers if searchable(marker) not in page]
        if missing:
            raise SystemExit(f"{url} lost required markers: {missing}")
        accessible += 1
    print(f"Validated {accessible} live Kerr County page contract(s).")


def validate_arcgis() -> None:
    service = fetch_json(f"{SERVICE}?f=json")
    if service.get("serviceItemId") != ITEM_ID:
        raise SystemExit(f"ArcGIS service item changed: {service.get('serviceItemId')!r}")
    metadata = fetch_json(f"{LAYER}?f=json")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise SystemExit(f"Unexpected geometry type: {metadata.get('geometryType')!r}")
    fields = {str(field.get("name") or "") for field in metadata.get("fields", [])}
    required = {FIELD, "order_num", "order_date", "effective_date"}
    if not required.issubset(fields):
        raise SystemExit(f"ArcGIS layer lost fields: {sorted(required - fields)}")
    query = urllib.parse.urlencode({
        "where": "1=1",
        "outFields": "precinct,order_num,order_date,effective_date",
        "returnGeometry": "false",
        "orderByFields": "precinct",
        "f": "json",
    })
    payload = fetch_json(f"{LAYER}/query?{query}")
    rows = [feature.get("attributes", {}) for feature in payload.get("features", [])]
    if len(rows) != 4 or {str(row.get(FIELD)) for row in rows} != {"1", "2", "3", "4"}:
        raise SystemExit(f"Unexpected live precinct rows: {rows!r}")
    if {str(row.get("order_num")) for row in rows} != {"39047"}:
        raise SystemExit("Live layer lost Court Order 39047.")
    if {row.get("order_date") for row in rows} != {1635919200000}:
        raise SystemExit("Live order date changed.")
    if {row.get("effective_date") for row in rows} != {1641016800000}:
        raise SystemExit("Live effective date changed.")
    print("Kerr County live ArcGIS contracts match the release.")


def main() -> None:
    validate_committed_evidence()
    validate_optional_pages()
    validate_arcgis()
    print("Kerr County roster, judicial appointment, scope, and source contracts are valid.")


if __name__ == "__main__":
    main()
