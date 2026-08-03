#!/usr/bin/env python3
"""Validate Galveston County roster, office-transition, and GIS source contracts."""

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

OFFICIALS = "https://www.galvestoncountytx.gov/our-county/elected-officials"
COURT = "https://www.galvestoncountytx.gov/our-county/county-judge/commissioners-court"
JUDGE = "https://www.galvestoncountytx.gov/our-county/county-judge"
COMMISSIONERS = [
    "https://www.galvestoncountytx.gov/our-county/commissioners/commissioner-1",
    "https://www.galvestoncountytx.gov/our-county/commissioners/commissioner-2",
    "https://www.galvestoncountytx.gov/our-county/commissioners/commissioner-3",
    "https://www.galvestoncountytx.gov/our-county/commissioners/commissioner-4",
]
SHERIFF = "https://sheriff.galvestoncountytx.gov/"
COUNTY_CLERK = "https://www.galvestoncountytx.gov/our-county/county-clerk"
DISTRICT_CLERK = "https://www.galvestoncountytx.gov/our-county/district-clerk"
TAX = "https://www.galvestoncountytx.gov/our-county/tax-assessor-collector"
TREASURY = "https://www.galvestoncountytx.gov/our-county/treasurer"
CUTOVER = "https://www.galvestoncountytx.gov/our-county/advanced-components/list-detail-pages/calendar-meeting-list/-sortn-EDate/-toggle-allpast/-sortd-desc/-npage-3"
CONSTITUTION = (
    "https://statutes.capitol.texas.gov/DocViewer.aspx?"
    "DocKey=CN%2FCN.16&ExactPhrase=False&HighlightType=1&"
    "Phrases=Galveston%7CCounty%7CTreasurer&QueryText=Galveston+County+Treasurer"
)
HJR = "https://capitol.texas.gov/tlodocs/88R/billtext/html/HJ00134F.htm"
EXPERIENCE_ID = "e0b0fef416cd42ad991b8ae95d22bb59"
EXPERIENCE_TITLE = "Galveston Final2"
EXPERIENCE_OWNER = "sigler_n"
PORTAL = "https://www.arcgis.com/sharing/rest"
LAYER = "https://services5.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Galveston_County_Commissioner_Precincts_2026/FeatureServer/0"
ROOT = LAYER.rsplit("/", 1)[0]
FIELD = "Commission"
EFFECTIVE_MS = int(datetime(2026, 6, 29, tzinfo=timezone.utc).timestamp() * 1000)

ROSTER_PATH = Path("data/raw/galveston-county/current-elected-offices.csv")
ABOLISHED_PATH = Path("data/raw/galveston-county/abolished-constitutional-offices.csv")
MANIFEST_PATH = Path("data/raw/galveston-county/source-manifest.csv")
CONTRACT_PATH = Path("data/raw/galveston-county/portal-source-contract.json")
ID_RE = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{32})(?![0-9a-fA-F])")

BROWSER_HEADERS = {
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


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers=BROWSER_HEADERS)


def fetch_json(url: str, attempts: int = 5) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(_request(url), timeout=45) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError(f"Expected JSON object from {url}")
            return payload
        except Exception as exc:  # network/provider drift is retried
            last_error = exc
            if attempt == attempts:
                raise
            time.sleep(attempt * 4)
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def fetch_html(url: str, *, optional: bool = False, attempts: int = 3) -> str | None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(_request(url), timeout=45) as response:
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
    if len(roster) != 9:
        raise SystemExit(f"Expected nine current Galveston elected-office rows, found {len(roster)}")
    actual_roster = {row["office_name"]: row["officeholder"] for row in roster}
    if actual_roster != EXPECTED_ROSTER:
        raise SystemExit(f"Committed Galveston roster changed unexpectedly: {actual_roster!r}")
    if len({row["officeholder"] for row in roster}) != 9:
        raise SystemExit("Committed Galveston roster contains duplicate current officeholders.")
    if "County Treasurer" in actual_roster:
        raise SystemExit("Abolished Galveston County Treasurer must not appear in the current roster.")

    with ABOLISHED_PATH.open(newline="", encoding="utf-8") as handle:
        abolished = list(csv.DictReader(handle))
    if len(abolished) != 1:
        raise SystemExit(f"Expected one abolished-office record, found {len(abolished)}")
    treasurer = abolished[0]
    expected_fields = {
        "office_name": "County Treasurer",
        "status": "abolished",
        "effective_date": "2024-01-01",
        "current_officeholder": "",
        "vacancy_status": "not_applicable",
    }
    for field, expected in expected_fields.items():
        if treasurer.get(field) != expected:
            raise SystemExit(
                f"Committed Galveston Treasurer transition changed {field}: "
                f"{treasurer.get(field)!r} != {expected!r}"
            )
    if "division of the County Clerk" not in treasurer.get("current_function_destination", ""):
        raise SystemExit("Committed Treasurer transition lost the County Clerk function destination.")

    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    if len(manifest) != 18:
        raise SystemExit(f"Expected 18 Galveston source records, found {len(manifest)}")
    source_ids = {row["source_id"] for row in manifest}
    if source_ids != REQUIRED_SOURCE_IDS:
        raise SystemExit(f"Committed Galveston source manifest changed unexpectedly: {source_ids!r}")
    manifest_by_id = {row["source_id"]: row for row in manifest}
    if "January 1, 2024" not in manifest_by_id["hjr-134-effective-date"]["use"]:
        raise SystemExit("Committed H.J.R. 134 evidence lost the abolition effective date.")
    if "June 29, 2026" not in manifest_by_id["galveston-2026-map-cutover"]["use"]:
        raise SystemExit("Committed map-cutover evidence lost the effective date.")
    if "does not establish a vacancy" not in manifest_by_id["galveston-stale-treasurer-directory"]["use"]:
        raise SystemExit("Committed stale-directory evidence lost the no-vacancy rule.")


def validate_optional_county_pages() -> None:
    accessible = 0

    officials_raw = fetch_html(OFFICIALS, optional=True)
    if officials_raw:
        accessible += 1
        require_aliases(searchable(officials_raw), "Galveston County elected-officials directory", ALIASES)

    court_raw = fetch_html(COURT, optional=True)
    if court_raw:
        accessible += 1
        require_aliases(searchable(court_raw), "Galveston County Commissioners Court page", ALIASES[:5])

    for url, options in zip([JUDGE, *COMMISSIONERS], ALIASES[:5], strict=True):
        page_raw = fetch_html(url, optional=True)
        if page_raw:
            accessible += 1
            require_aliases(searchable(page_raw), url, (options,))

    for url, options in (
        (SHERIFF, ALIASES[5]),
        (COUNTY_CLERK, ALIASES[6]),
        (DISTRICT_CLERK, ALIASES[7]),
        (TAX, ALIASES[8]),
    ):
        page_raw = fetch_html(url, optional=True)
        if page_raw:
            accessible += 1
            require_aliases(searchable(page_raw), url, (options,))

    treasury_raw = fetch_html(TREASURY, optional=True)
    if treasury_raw:
        accessible += 1
        treasury = searchable(treasury_raw)
        if "treasury" not in treasury or "division of the county clerk" not in treasury:
            raise SystemExit("Galveston County Treasury page lost the County Clerk division structure.")

    cutover_raw = fetch_html(CUTOVER, optional=True)
    if cutover_raw:
        accessible += 1
        cutover = searchable(cutover_raw)
        if "commissioner" not in cutover or "precinct" not in cutover:
            raise SystemExit("Galveston County cutover announcement lost Commissioner-precinct context.")
        if not any(marker in cutover for marker in ("6 29 2026", "06 29 2026", "june 29 2026")):
            raise SystemExit("Galveston County cutover announcement lost the June 29, 2026 effective date.")

    print(
        f"Validated {accessible} live Galveston County page(s); CivicPlus-blocked pages "
        "are covered by the committed 18-source hierarchy and live state-law/ArcGIS authorities."
    )


def validate_state_authorities() -> None:
    constitution_raw = fetch_html(CONSTITUTION, optional=True)
    if constitution_raw:
        constitution = searchable(constitution_raw)
        for marker in ("galveston", "treasurer", "abolished"):
            if marker not in constitution:
                raise SystemExit(f"Texas Constitution DocViewer lost marker: {marker}")
        if "sec 44" not in constitution and "section 44" not in constitution:
            raise SystemExit("Texas Constitution DocViewer lost Section 44 context.")

    # The enrolled resolution is required live. It supplies both the constitutional
    # amendment text and the January 1, 2024 effective-date provision.
    hjr = searchable(fetch_html(HJR) or "")
    for marker in ("galveston county", "county treasurer", "abolished", "january 1 2024"):
        if marker not in hjr:
            raise SystemExit(f"H.J.R. 134 lost abolition marker: {marker}")


def validate_contract_and_portal() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["experience_item_id"] == EXPERIENCE_ID
    assert contract["experience_item_title"] == EXPERIENCE_TITLE
    assert contract["experience_item_owner"] == EXPERIENCE_OWNER
    assert contract["effective_date"] == "2026-06-29"
    assert contract["operational_layer_url"] == LAYER
    assert contract["district_field"] == FIELD
    assert contract["district_values"] == ["1", "2", "3", "4"]
    selected = contract["selected_candidate"]
    assert selected["layer_url"] == LAYER
    assert selected["post_cutover"] is True
    assert selected["referenced_by_experience_graph"] is True
    assert any("pre-cutover" in candidate["rejection_reason"] for candidate in contract["rejected_candidates"])

    experience = fetch_json(f"{PORTAL}/content/items/{EXPERIENCE_ID}?f=json")
    if (
        experience.get("id") != EXPERIENCE_ID
        or experience.get("title") != EXPERIENCE_TITLE
        or experience.get("owner") != EXPERIENCE_OWNER
    ):
        raise SystemExit(f"Unexpected Galveston Experience metadata: {experience!r}")

    experience_data = fetch_json(f"{PORTAL}/content/items/{EXPERIENCE_ID}/data?f=json")
    graph_texts = [json.dumps(experience_data, sort_keys=True)]
    for item_id in sorted(set(ID_RE.findall(graph_texts[0])))[:24]:
        try:
            metadata = fetch_json(f"{PORTAL}/content/items/{item_id}?f=json", attempts=2)
            data = fetch_json(f"{PORTAL}/content/items/{item_id}/data?f=json", attempts=2)
        except Exception:
            continue
        graph_texts.extend([json.dumps(metadata, sort_keys=True), json.dumps(data, sort_keys=True)])

    service = fetch_json(f"{ROOT}?f=json")
    service_item_id = str(service.get("serviceItemId") or "")
    graph_text = "\n".join(graph_texts).lower()
    if not (
        ROOT.lower() in graph_text
        or LAYER.lower() in graph_text
        or (service_item_id and service_item_id.lower() in graph_text)
    ):
        raise SystemExit("The public Experience graph no longer references the dedicated 2026 service.")

    service_item = fetch_json(f"{PORTAL}/content/items/{service_item_id}?f=json") if service_item_id else {}
    metadata = fetch_json(f"{LAYER}?f=json")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise SystemExit(f"Unexpected Galveston Commissioner geometry type: {metadata.get('geometryType')!r}")
    fields = {str(field.get("name") or "") for field in metadata.get("fields", [])}
    if FIELD not in fields:
        raise SystemExit(f"Galveston Commissioner layer lost {FIELD}: {sorted(fields)}")

    params = urllib.parse.urlencode(
        {
            "where": "1=1",
            "outFields": FIELD,
            "returnGeometry": "false",
            "orderByFields": FIELD,
            "f": "json",
        }
    )
    payload = fetch_json(f"{LAYER}/query?{params}")
    values: list[str] = []
    for feature in payload.get("features", []):
        text = str(feature.get("attributes", {}).get(FIELD) or "")
        match = re.search(r"(?<!\d)([1-4])(?!\d)", text)
        if match:
            values.append(match.group(1))
    if {value: values.count(value) for value in sorted(set(values))} != {
        "1": 1,
        "2": 1,
        "3": 1,
        "4": 1,
    }:
        raise SystemExit(f"Unexpected Galveston Commissioner values: {values!r}")

    dates = [
        int(service_item.get("created") or 0),
        int(service_item.get("modified") or 0),
        int((service.get("editingInfo") or {}).get("lastEditDate") or 0),
        int((metadata.get("editingInfo") or {}).get("lastEditDate") or 0),
    ]
    if max(dates) < EFFECTIVE_MS:
        raise SystemExit("Dedicated 2026 Galveston service lost post-cutover item/layer evidence.")

    live_pre_cutover = 0
    for candidate in contract["rejected_candidates"]:
        item_id = str(candidate.get("service_item_id") or "")
        if not item_id or "pre-cutover" not in candidate.get("rejection_reason", ""):
            continue
        item = fetch_json(f"{PORTAL}/content/items/{item_id}?f=json")
        item_dates = [int(item.get("created") or 0), int(item.get("modified") or 0)]
        if max(item_dates) and max(item_dates) < EFFECTIVE_MS:
            live_pre_cutover += 1
    if live_pre_cutover < 1:
        raise SystemExit("No rejected legacy ArcGIS item remains proven pre-cutover.")


def main() -> None:
    validate_committed_county_evidence()
    validate_optional_county_pages()
    validate_state_authorities()
    validate_contract_and_portal()
    print(
        "Galveston County committed roster, abolished-office, live state-law, "
        "cutover, Experience, legacy-item, and layer contracts match the release."
    )


if __name__ == "__main__":
    main()
