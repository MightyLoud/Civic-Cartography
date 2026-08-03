#!/usr/bin/env python3
"""Validate Galveston County roster, office-transition, and GIS source contracts."""

from __future__ import annotations

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
CONSTITUTION = "https://statutes.capitol.texas.gov/Docs/CN/htm/CN.16.htm"
HJR = "https://capitol.texas.gov/tlodocs/88R/billtext/html/HJ00134F.htm"
CUTOVER = "https://www.galvestoncountytx.gov/our-county/advanced-components/list-detail-pages/calendar-meeting-list/-sortn-EDate/-toggle-allpast/-sortd-desc/-npage-3"
EXPERIENCE_ID = "e0b0fef416cd42ad991b8ae95d22bb59"
EXPERIENCE_TITLE = "Galveston Final2"
EXPERIENCE_OWNER = "sigler_n"
PORTAL = "https://www.arcgis.com/sharing/rest"
LAYER = "https://services5.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Galveston_County_Commissioner_Precincts_2026/FeatureServer/0"
ROOT = LAYER.rsplit("/", 1)[0]
FIELD = "Commission"
EFFECTIVE_MS = int(datetime(2026, 6, 29, tzinfo=timezone.utc).timestamp() * 1000)
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
                print(f"Optional corroborating page blocked with HTTP {exc.code}: {url}")
                return None
            if attempt == attempts:
                raise
            time.sleep(attempt * 4)
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                if optional:
                    print(f"Optional corroborating page unavailable: {url}: {exc}")
                    return None
                raise
            time.sleep(attempt * 4)
    if optional:
        print(f"Optional corroborating page unavailable: {url}: {last_error}")
        return None
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def searchable(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def require_aliases(page: str, label: str, aliases: tuple[tuple[str, ...], ...]) -> None:
    for options in aliases:
        if not any(option in page for option in options):
            raise SystemExit(f"{label} lost current holder variants: {options!r}")


def validate_county_pages() -> None:
    officials_raw = fetch_html(OFFICIALS, optional=True)
    if officials_raw:
        require_aliases(searchable(officials_raw), "Galveston County elected-officials directory", ALIASES)

    court = searchable(fetch_html(COURT) or "")
    require_aliases(court, "Galveston County Commissioners Court page", ALIASES[:5])

    # Court controls the five-member court. Individual court pages are corroborating
    # because the county's CivicPlus site may block burst requests from CI runners.
    for url, options in zip([JUDGE, *COMMISSIONERS], ALIASES[:5], strict=True):
        page_raw = fetch_html(url, optional=True)
        if page_raw:
            require_aliases(searchable(page_raw), url, (options,))

    required_individual = (
        (SHERIFF, ALIASES[5]),
        (COUNTY_CLERK, ALIASES[6]),
        (DISTRICT_CLERK, ALIASES[7]),
        (TAX, ALIASES[8]),
    )
    for url, options in required_individual:
        page = searchable(fetch_html(url) or "")
        require_aliases(page, url, (options,))

    treasury = searchable(fetch_html(TREASURY) or "")
    if "treasury" not in treasury or "division of the county clerk" not in treasury:
        raise SystemExit("Galveston County Treasury page lost the County Clerk division structure.")

    constitution = searchable(fetch_html(CONSTITUTION) or "")
    for marker in ("galveston county", "county treasurer", "abolished"):
        if marker not in constitution:
            raise SystemExit(f"Texas Constitution lost Galveston Treasurer abolition marker: {marker}")

    hjr = searchable(fetch_html(HJR) or "")
    for marker in ("galveston county", "county treasurer", "january 1 2024"):
        if marker not in hjr:
            raise SystemExit(f"H.J.R. 134 lost abolition marker: {marker}")

    cutover = searchable(fetch_html(CUTOVER) or "")
    if "commissioner" not in cutover or "precinct" not in cutover:
        raise SystemExit("Galveston County cutover announcement lost Commissioner-precinct context.")
    if not any(marker in cutover for marker in ("6 29 2026", "06 29 2026", "june 29 2026")):
        raise SystemExit("Galveston County cutover announcement lost the June 29, 2026 effective date.")


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
    validate_county_pages()
    validate_contract_and_portal()
    print(
        "Galveston County roster, abolished-office, cutover, Experience, "
        "legacy-item, and layer contracts match the release."
    )


if __name__ == "__main__":
    main()
