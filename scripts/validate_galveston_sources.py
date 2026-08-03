#!/usr/bin/env python3
"""Validate Galveston County roster, transition, and ArcGIS source contracts."""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COUNTY_BASE = "https://www.galvestoncountytx.gov"
OFFICIALS = f"{COUNTY_BASE}/our-county/elected-officials"
COURT = f"{COUNTY_BASE}/our-county/county-judge/commissioners-court"
JUDGE = f"{COUNTY_BASE}/our-county/county-judge"
COMMISSIONERS = [
    f"{COUNTY_BASE}/our-county/commissioners/commissioner-{number}"
    for number in range(1, 5)
]
SHERIFF = "https://sheriff.galvestoncountytx.gov/"
COUNTY_CLERK = f"{COUNTY_BASE}/our-county/county-clerk"
DISTRICT_CLERK = f"{COUNTY_BASE}/our-county/district-clerk"
TAX = f"{COUNTY_BASE}/our-county/tax-assessor-collector"
TREASURY = f"{COUNTY_BASE}/our-county/treasurer"
CUTOVER = (
    f"{COUNTY_BASE}/our-county/advanced-components/list-detail-pages/"
    "calendar-meeting-list/-sortn-EDate/-toggle-allpast/-sortd-desc/-npage-3"
)
HJR = "https://capitol.texas.gov/tlodocs/88R/billtext/html/HJ00134F.htm"

EXPERIENCE_ID = "e0b0fef416cd42ad991b8ae95d22bb59"
EXPERIENCE_TITLE = "Galveston Final2"
EXPERIENCE_OWNER = "sigler_n"
PORTAL = "https://www.arcgis.com/sharing/rest"
LAYER = (
    "https://services5.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/"
    "Galveston_County_Commissioner_Precincts_2026/FeatureServer/0"
)
ROOT = LAYER.rsplit("/", 1)[0]
FIELD = "Commission"
EFFECTIVE_MS = int(datetime(2026, 6, 29, tzinfo=timezone.utc).timestamp() * 1000)
ID_RE = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{32})(?![0-9a-fA-F])")

ROSTER_PATH = Path("data/raw/galveston-county/current-elected-offices.csv")
ABOLISHED_PATH = Path("data/raw/galveston-county/abolished-constitutional-offices.csv")
MANIFEST_PATH = Path("data/raw/galveston-county/source-manifest.csv")
CONTRACT_PATH = Path("data/raw/galveston-county/portal-source-contract.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

ALIASES: tuple[tuple[str, ...], ...] = (
    ("mark a henry", "mark henry"),
    ("darrell apffel",),
    ("joe giusti",),
    ("hank dugie",),
    ("dr robin armstrong", "robin armstrong"),
    ("jimmy fullen",),
    ("dwight d sullivan", "dwight sullivan"),
    ("john d kinard", "john kinard"),
    ("cheryl e johnson", "cheryl johnson"),
)

EXPECTED_ROSTER = {
    "County Judge": "Mark A. Henry",
    "County Commissioner Precinct 1": "Darrell Apffel",
    "County Commissioner Precinct 2": "Joe Giusti",
    "County Commissioner Precinct 3": "Hank Dugie",
    "County Commissioner Precinct 4": "Dr. Robin Armstrong",
    "Sheriff": "Jimmy Fullen",
    "County Clerk": "Dwight D. Sullivan",
    "District Clerk": "John D. Kinard",
    "Tax Assessor-Collector": "Cheryl E. Johnson",
}

REQUIRED_SOURCE_IDS = {
    "galveston-elected-officials",
    "galveston-commissioners-court",
    "galveston-county-judge",
    "galveston-commissioner-1",
    "galveston-commissioner-2",
    "galveston-commissioner-3",
    "galveston-commissioner-4",
    "galveston-sheriff",
    "galveston-county-clerk",
    "galveston-district-clerk",
    "galveston-tax-assessor",
    "galveston-treasury-division",
    "texas-constitution-galveston-treasurer",
    "hjr-134-effective-date",
    "galveston-stale-treasurer-directory",
    "galveston-2026-map-cutover",
    "galveston-arcgis-experience",
    "census-galveston-county",
}


def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers=HEADERS)


def fetch_json(url: str, attempts: int = 5) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request(url), timeout=45) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError(f"Expected JSON object from {url}")
            return payload
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                raise
            time.sleep(attempt * 4)
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def fetch_html(url: str, *, optional: bool = False, attempts: int = 3) -> str | None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request(url), timeout=45) as response:
                return html.unescape(response.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if optional and exc.code in {403, 429}:
                print(f"Optional source page blocked with HTTP {exc.code}: {url}")
                return None
            if attempt == attempts:
                raise
            time.sleep(attempt * 4)
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                if optional:
                    print(f"Optional source page unavailable: {url}: {exc}")
                    return None
                raise
            time.sleep(attempt * 4)
    if optional:
        print(f"Optional source page unavailable: {url}: {last_error}")
        return None
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def searchable(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def require_aliases(page: str, label: str, aliases: tuple[tuple[str, ...], ...]) -> None:
    for options in aliases:
        if not any(option in page for option in options):
            raise SystemExit(f"{label} lost current holder variants: {options!r}")


def validate_committed_county_evidence() -> None:
    with ROSTER_PATH.open(newline="", encoding="utf-8") as handle:
        roster = list(csv.DictReader(handle))
    actual = {row["office_name"]: row["officeholder"] for row in roster}
    if len(roster) != 9 or actual != EXPECTED_ROSTER:
        raise SystemExit(f"Committed Galveston roster changed unexpectedly: {actual!r}")
    if len({row["officeholder"] for row in roster}) != 9:
        raise SystemExit("Committed Galveston roster contains duplicate holders.")
    if "County Treasurer" in actual:
        raise SystemExit("Abolished County Treasurer must not appear in the current roster.")

    with ABOLISHED_PATH.open(newline="", encoding="utf-8") as handle:
        abolished = list(csv.DictReader(handle))
    if len(abolished) != 1:
        raise SystemExit(f"Expected one abolished-office record, found {len(abolished)}")
    treasurer = abolished[0]
    expected = {
        "office_name": "County Treasurer",
        "status": "abolished",
        "effective_date": "2024-01-01",
        "current_officeholder": "",
        "vacancy_status": "not_applicable",
    }
    for field, value in expected.items():
        if treasurer.get(field) != value:
            raise SystemExit(f"Abolished-office field changed: {field}={treasurer.get(field)!r}")
    if "division of the County Clerk" not in treasurer["current_function_destination"]:
        raise SystemExit("Treasurer transition lost the County Clerk destination.")

    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    source_ids = {row["source_id"] for row in manifest}
    if len(manifest) != 18 or source_ids != REQUIRED_SOURCE_IDS:
        raise SystemExit(f"Committed Galveston source manifest changed: {source_ids!r}")
    by_id = {row["source_id"]: row for row in manifest}
    required_text = {
        "hjr-134-effective-date": "January 1, 2024",
        "galveston-2026-map-cutover": "June 29, 2026",
        "galveston-stale-treasurer-directory": "does not establish a vacancy",
    }
    for source_id, marker in required_text.items():
        if marker not in by_id[source_id]["use"]:
            raise SystemExit(f"Source manifest lost marker for {source_id}: {marker}")


def validate_optional_county_pages() -> None:
    accessible = 0
    page_contracts: list[tuple[str, tuple[tuple[str, ...], ...]]] = [
        (OFFICIALS, ALIASES),
        (COURT, ALIASES[:5]),
        (JUDGE, (ALIASES[0],)),
        *[(url, (ALIASES[index],)) for index, url in enumerate(COMMISSIONERS, start=1)],
        (SHERIFF, (ALIASES[5],)),
        (COUNTY_CLERK, (ALIASES[6],)),
        (DISTRICT_CLERK, (ALIASES[7],)),
        (TAX, (ALIASES[8],)),
    ]
    for url, aliases in page_contracts:
        raw = fetch_html(url, optional=True)
        if raw:
            accessible += 1
            require_aliases(searchable(raw), url, aliases)

    treasury_raw = fetch_html(TREASURY, optional=True)
    if treasury_raw:
        accessible += 1
        treasury = searchable(treasury_raw)
        if "treasury" not in treasury or "division of the county clerk" not in treasury:
            raise SystemExit("Treasury page lost the County Clerk division structure.")

    cutover_raw = fetch_html(CUTOVER, optional=True)
    if cutover_raw:
        accessible += 1
        cutover = searchable(cutover_raw)
        if "commissioner" not in cutover or "precinct" not in cutover:
            raise SystemExit("Cutover page lost Commissioner-precinct context.")
        if not any(value in cutover for value in ("6 29 2026", "06 29 2026", "june 29 2026")):
            raise SystemExit("Cutover page lost the June 29, 2026 date.")

    print(
        f"Validated {accessible} live Galveston County page(s); blocked pages are "
        "covered by committed evidence and live enrolled-law/ArcGIS authorities."
    )


def validate_enrolled_authority() -> None:
    hjr = searchable(fetch_html(HJR) or "")
    for marker in (
        "galveston county",
        "county treasurer",
        "abolished",
        "january 1 2024",
    ):
        if marker not in hjr:
            raise SystemExit(f"H.J.R. 134 lost abolition marker: {marker}")


def validate_contract_and_portal() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = {
        "experience_item_id": EXPERIENCE_ID,
        "experience_item_title": EXPERIENCE_TITLE,
        "experience_item_owner": EXPERIENCE_OWNER,
        "effective_date": "2026-06-29",
        "operational_layer_url": LAYER,
        "district_field": FIELD,
        "district_values": ["1", "2", "3", "4"],
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            raise SystemExit(f"Committed portal contract changed: {field}={contract.get(field)!r}")
    selected = contract["selected_candidate"]
    if not (
        selected["layer_url"] == LAYER
        and selected["post_cutover"] is True
        and selected["referenced_by_experience_graph"] is True
    ):
        raise SystemExit(f"Selected Galveston portal candidate changed: {selected!r}")
    if not any("pre-cutover" in row["rejection_reason"] for row in contract["rejected_candidates"]):
        raise SystemExit("Portal contract lost pre-cutover rejection evidence.")

    experience = fetch_json(f"{PORTAL}/content/items/{EXPERIENCE_ID}?f=json")
    if (
        experience.get("id") != EXPERIENCE_ID
        or experience.get("title") != EXPERIENCE_TITLE
        or experience.get("owner") != EXPERIENCE_OWNER
    ):
        raise SystemExit(f"Unexpected Experience metadata: {experience!r}")

    experience_data = fetch_json(f"{PORTAL}/content/items/{EXPERIENCE_ID}/data?f=json")
    graph_parts = [json.dumps(experience_data, sort_keys=True)]
    for item_id in sorted(set(ID_RE.findall(graph_parts[0])))[:24]:
        try:
            graph_parts.append(
                json.dumps(fetch_json(f"{PORTAL}/content/items/{item_id}?f=json", attempts=2), sort_keys=True)
            )
            graph_parts.append(
                json.dumps(fetch_json(f"{PORTAL}/content/items/{item_id}/data?f=json", attempts=2), sort_keys=True)
            )
        except Exception:
            continue

    service = fetch_json(f"{ROOT}?f=json")
    service_item_id = str(service.get("serviceItemId") or "")
    graph = "\n".join(graph_parts).lower()
    if not (
        ROOT.lower() in graph
        or LAYER.lower() in graph
        or (service_item_id and service_item_id.lower() in graph)
    ):
        raise SystemExit("Experience graph no longer references the dedicated 2026 service.")

    service_item = fetch_json(f"{PORTAL}/content/items/{service_item_id}?f=json") if service_item_id else {}
    metadata = fetch_json(f"{LAYER}?f=json")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise SystemExit(f"Unexpected Commissioner geometry type: {metadata.get('geometryType')!r}")
    fields = {str(field.get("name") or "") for field in metadata.get("fields", [])}
    if FIELD not in fields:
        raise SystemExit(f"Commissioner layer lost {FIELD}: {sorted(fields)}")

    query = urllib.parse.urlencode(
        {
            "where": "1=1",
            "outFields": FIELD,
            "returnGeometry": "false",
            "orderByFields": FIELD,
            "f": "json",
        }
    )
    payload = fetch_json(f"{LAYER}/query?{query}")
    values: list[str] = []
    for feature in payload.get("features", []):
        match = re.search(
            r"(?<!\d)([1-4])(?!\d)",
            str(feature.get("attributes", {}).get(FIELD) or ""),
        )
        if match:
            values.append(match.group(1))
    counts = {value: values.count(value) for value in sorted(set(values))}
    if counts != {"1": 1, "2": 1, "3": 1, "4": 1}:
        raise SystemExit(f"Unexpected Commissioner values: {counts!r}")

    dates = [
        int(service_item.get("created") or 0),
        int(service_item.get("modified") or 0),
        int((service.get("editingInfo") or {}).get("lastEditDate") or 0),
        int((metadata.get("editingInfo") or {}).get("lastEditDate") or 0),
    ]
    if max(dates) < EFFECTIVE_MS:
        raise SystemExit("Dedicated 2026 service lost post-cutover evidence.")

    live_pre_cutover = 0
    for candidate in contract["rejected_candidates"]:
        item_id = str(candidate.get("service_item_id") or "")
        if not item_id or "pre-cutover" not in candidate.get("rejection_reason", ""):
            continue
        item = fetch_json(f"{PORTAL}/content/items/{item_id}?f=json")
        dates = [int(item.get("created") or 0), int(item.get("modified") or 0)]
        if max(dates) and max(dates) < EFFECTIVE_MS:
            live_pre_cutover += 1
    if live_pre_cutover < 1:
        raise SystemExit("No rejected legacy ArcGIS item remains proven pre-cutover.")


def main() -> None:
    validate_committed_county_evidence()
    validate_optional_county_pages()
    validate_enrolled_authority()
    validate_contract_and_portal()
    print(
        "Galveston County committed roster, abolished-office, enrolled state-law, "
        "Experience, legacy-item, and layer contracts match the release."
    )


if __name__ == "__main__":
    main()
