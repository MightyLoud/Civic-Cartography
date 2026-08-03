#!/usr/bin/env python3
"""Validate Kerr County roster, judicial appointment, scope, and GIS contracts."""
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

COURT = 'https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-commissioners-court'
ELECTIONS = 'https://www.kerrcountytx.gov/voting-in-kerr-county/kerr-county-elections'
SHERIFF = 'https://www.kerrcountysheriff.com/about-the-kerr-county-sheriff-s-office'
COUNTY_CLERK = 'https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-clerk'
COUNTY_CLERK_APPOINTMENT = 'https://kerrcountytx.gov/blog/nadene-alford-appointed-by-court-as-new-kerr-county-clerk'
DISTRICT_CLERK = 'https://www.kerrcountytx.gov/kerr-county-all-departments/clerk-of-the-district-courts-of-kerr-county'
DISTRICT_CLERK_APPOINTMENT = 'https://kerrcountytx.gov/blog/district-clerk-to-retire-march-31-appointment-made-to-serve-out-term'
BAIL_BOARD = 'https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-treasurer/kerr-county-bail-bond-board'
TAX = 'https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-tax-assessor-collector'
TREASURER = 'https://www.kerrcountytx.gov/kerr-county-all-departments/kerr-county-treasurer'
SURVEYOR = 'https://kerrcountytx.gov/kerr-county-all-departments/kerr-county-surveyor'
QUALIFICATIONS = 'https://www.sos.texas.gov/elections/candidates/guide/2026/qualifications2026.shtml'
LAYER = 'https://services1.arcgis.com/Ijqs2ihddUy84otW/ArcGIS/rest/services/Kerr_County_Commissioner_Precincts_2022/FeatureServer/0'
SERVICE = 'https://services1.arcgis.com/Ijqs2ihddUy84otW/ArcGIS/rest/services/Kerr_County_Commissioner_Precincts_2022/FeatureServer'
ITEM_ID = "de7c8e02045a4981a752998bb6406538"
FIELD = "precinct"
ROSTER_PATH = Path("data/raw/kerr-county/current-elected-offices.csv")
TRANSITION_PATH = Path("data/raw/kerr-county/district-clerk-transition.csv")
NON_SCOPE_PATH = Path("data/raw/kerr-county/non-scope-offices.csv")
MANIFEST_PATH = Path("data/raw/kerr-county/source-manifest.csv")
CONTRACT_PATH = Path("data/raw/kerr-county/gis-source-contract.json")

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
REQUIRED_SOURCE_IDS = [
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
    "census-kerr-county"
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Civic-Cartography-validator/1.0",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers=HEADERS)

def fetch_json(url: str, attempts: int = 5) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request(url), timeout=45) as response:
                value = json.load(response)
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object from {url}")
            return value
        except Exception as exc:
            last = exc
            if attempt == attempts:
                raise
            time.sleep(attempt * 4)
    raise RuntimeError(last)

def fetch_html(url: str, optional: bool = True, attempts: int = 3) -> str | None:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request(url), timeout=45) as response:
                return html.unescape(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            last = exc
            if optional and exc.code in {403, 404, 429}:
                print(f"Optional page blocked with HTTP {exc.code}: {url}")
                return None
        except Exception as exc:
            last = exc
        if attempt < attempts:
            time.sleep(attempt * 4)
    if optional:
        print(f"Optional page unavailable: {url}: {last}")
        return None
    raise RuntimeError(f"Unable to fetch {url}: {last}")

def searchable(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

def require_all(page: str, label: str, markers: tuple[str, ...]) -> None:
    missing = [marker for marker in markers if searchable(marker) not in page]
    if missing:
        raise SystemExit(f"{label} lost required markers: {missing}")

def validate_committed_evidence() -> None:
    with ROSTER_PATH.open(newline="", encoding="utf-8") as handle:
        roster = list(csv.DictReader(handle))
    actual = {row["office_name"]: row["officeholder"] for row in roster}
    if len(roster) != 10 or actual != EXPECTED_ROSTER:
        raise SystemExit(f"Committed Kerr County roster changed: {actual!r}")
    if len({row["officeholder"] for row in roster}) != 10:
        raise SystemExit("Kerr County roster contains duplicate current holders.")
    methods = [row["selection_method"] for row in roster]
    if methods.count("election") != 9 or methods.count("judicial_appointment") != 1:
        raise SystemExit(f"Unexpected Kerr County current-holder selection methods: {methods!r}")
    appointed = next(row for row in roster if row["selection_method"] == "judicial_appointment")
    if appointed["office_name"] != "District Clerk" or "Dawn Lantz" not in appointed["notes"]:
        raise SystemExit(f"District Clerk transition lost from roster: {appointed!r}")

    with TRANSITION_PATH.open(newline="", encoding="utf-8") as handle:
        transitions = list(csv.DictReader(handle))
    if len(transitions) != 1:
        raise SystemExit(f"Expected one Kerr County transition row, found {len(transitions)}")
    transition = transitions[0]
    expected = {
        "office_name": "District Clerk",
        "office_status": "elected_office",
        "current_officeholder": "Eunavae Baublit Tonroy",
        "selection_method": "judicial_appointment",
        "predecessor": "Dawn Lantz",
        "predecessor_last_day": "2026-03-31",
        "appointment_announced_date": "2026-03-16",
        "current_service_start": "2026-04-01",
    }
    for field, value in expected.items():
        if transition.get(field) != value:
            raise SystemExit(f"Kerr transition changed: {field}={transition.get(field)!r}")
    for marker in ("M. Patrick Maguire", "Albert D. Pattillo III"):
        if marker not in transition["appointing_authorities"]:
            raise SystemExit(f"Kerr transition lost appointing judge: {marker}")

    with NON_SCOPE_PATH.open(newline="", encoding="utf-8") as handle:
        non_scope = list(csv.DictReader(handle))
    surveyor_row = next((row for row in non_scope if row["office_name"] == "County Surveyor"), None)
    if not surveyor_row or "Lee C. Voelkel" not in surveyor_row["current_officeholder"]:
        raise SystemExit("Kerr County Surveyor non-scope evidence is missing.")
    if "County Surveyor" in actual:
        raise SystemExit("County Surveyor leaked into the bounded ten-office release.")

    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    source_ids = {row["source_id"] for row in manifest}
    if len(manifest) != 18 or source_ids != set(REQUIRED_SOURCE_IDS):
        raise SystemExit(f"Kerr source manifest changed: {source_ids!r}")
    by_id = {row["source_id"]: row for row in manifest}
    for source_id, marker in {
        "kerr-elections-current-officeholders": "Dawn Lantz",
        "kerr-county-clerk-2024-appointment-expiry": "December 31, 2024",
        "kerr-district-clerk-appointment": "joint selection",
        "kerr-county-surveyor": "outside the bounded ten-office release",
        "kerr-arcgis-precinct-layer": "Court Order 39047",
    }.items():
        if marker not in by_id[source_id]["use"]:
            raise SystemExit(f"Manifest lost {marker!r} in {source_id}")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected_contract = {
        "service_item_id": ITEM_ID,
        "operational_layer_id": 0,
        "operational_layer_url": LAYER,
        "geometry_type": "esriGeometryPolygon",
        "district_field": FIELD,
        "district_values": ["1", "2", "3", "4"],
        "resolved_from_county_elections_page": True,
    }
    for field, value in expected_contract.items():
        if contract.get(field) != value:
            raise SystemExit(f"Kerr GIS contract changed: {field}={contract.get(field)!r}")
    rows = contract.get("source_rows", [])
    if len(rows) != 4 or {str(row.get(FIELD)) for row in rows} != {"1", "2", "3", "4"}:
        raise SystemExit(f"Kerr GIS contract lost precinct rows: {rows!r}")
    if {str(row.get("order_num")) for row in rows} != {"39047"}:
        raise SystemExit("Kerr GIS contract lost Court Order 39047.")
    if {row.get("order_date") for row in rows} != {1635919200000}:
        raise SystemExit("Kerr GIS contract order date changed.")
    if {row.get("effective_date") for row in rows} != {1641016800000}:
        raise SystemExit("Kerr GIS contract effective date changed.")

def validate_optional_pages() -> None:
    contracts = [
        (COURT, ("Rob Kelly", "Tom Jones", "Rich Paces", "Jeff Holt", "Don Harris")),
        (ELECTIONS, ("Larry L. Leitha Jr", "Tracy Soldan", "Bob Reeves", "Nadene Alford", "Dawn Lantz", "Lee Voelkel")),
        (SHERIFF, ("Larry L. Leitha", "elected in 2020")),
        (COUNTY_CLERK, ("Nadene Alford", "County Clerk")),
        (COUNTY_CLERK_APPOINTMENT, ("December 31, 2024", "Nadene Alford")),
        (DISTRICT_CLERK, ("Eunavae Baublit", "District Clerk")),
        (DISTRICT_CLERK_APPOINTMENT, ("Dawn Lantz", "March 31", "Eunavae Baublit Tonroy", "M. Patrick Maguire", "Albert D. Pattillo III")),
        (BAIL_BOARD, ("Eunavae Baublit", "Nadene Alford", "M. Patrick Maguire", "Albert D. Patillo")),
        (TAX, ("Bob Reeves", "Tax Assessor")),
        (TREASURER, ("Tracy Soldan", "voters elect the treasurer", "four years")),
        (SURVEYOR, ("Lee Voelkel", "County Surveyor")),
        (QUALIFICATIONS, ("District Clerk", "4 years")),
    ]
    accessible = 0
    for url, markers in contracts:
        raw = fetch_html(url, optional=True)
        if raw:
            accessible += 1
            require_all(searchable(raw), url, markers)
    print(f"Validated {accessible} live Kerr County/statutory page contract(s); unavailable pages remain covered by committed evidence.")

def validate_arcgis() -> None:
    service = fetch_json(f"{SERVICE}?f=json")
    if service.get("serviceItemId") != ITEM_ID:
        raise SystemExit(f"Kerr ArcGIS service item changed: {service.get('serviceItemId')!r}")
    metadata = fetch_json(f"{LAYER}?f=json")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise SystemExit(f"Unexpected Kerr geometry type: {metadata.get('geometryType')!r}")
    fields = {str(field.get("name") or "") for field in metadata.get("fields", [])}
    required = {FIELD, "order_num", "order_date", "effective_date"}
    if not required.issubset(fields):
        raise SystemExit(f"Kerr ArcGIS layer lost fields: {sorted(required - fields)}")
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
        raise SystemExit(f"Unexpected Kerr precinct rows: {rows!r}")
    if {str(row.get("order_num")) for row in rows} != {"39047"}:
        raise SystemExit("Live Kerr precinct layer lost Court Order 39047.")
    if {row.get("order_date") for row in rows} != {1635919200000}:
        raise SystemExit("Live Kerr precinct order date changed.")
    if {row.get("effective_date") for row in rows} != {1641016800000}:
        raise SystemExit("Live Kerr precinct effective date changed.")
    print("Kerr County live ArcGIS polygon, stable-field, order, and effective-date contracts match the release.")

def main() -> None:
    validate_committed_evidence()
    validate_optional_pages()
    validate_arcgis()
    print("Kerr County roster, judicial appointment, scope, and source contracts are valid.")

if __name__ == "__main__":
    main()
