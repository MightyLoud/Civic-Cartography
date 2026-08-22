#!/usr/bin/env python3
"""Validate the Tarrant ArcGIS source hierarchy without treating shells as data.

Metadata is advisory evidence for the source hierarchy.  The dedicated workflow
still performs exact feature queries and byte/semantic snapshot comparisons; those
steps remain blocking.  Empty JSON, ArcGIS error envelopes, and generic REST
Directory bootstrap pages are recorded as unavailable rather than interpreted as
source drift.  Populated layer metadata that contradicts the retained hierarchy
still fails closed.
"""

from __future__ import annotations

import hashlib
import html
import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json,text/html,text/plain,*/*",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
URLS = {
    "controlling": (
        "https://mapit.tarrantcounty.com/arcgis/rest/services/"
        "BondProject/BondProjects/MapServer/3"
    ),
    "general": (
        "https://mapit.tarrantcounty.com/arcgis/rest/services/"
        "Dynamic/CommissionerPrecinct/MapServer/0"
    ),
    "stale_2010": (
        "https://mapit.tarrantcounty.com/arcgis/rest/services/"
        "Dynamic/CommPct_Outline/MapServer"
    ),
}
STATUS_OUTPUT = Path("build/tarrant-county/metadata-status.json")
Validator = Callable[[dict[str, Any]], None]
HtmlValidator = Callable[[str], None]


class MetadataUnavailable(ValueError):
    """The server returned no authoritative layer metadata."""


class PopulatedMetadataDrift(ValueError):
    """A populated official response contradicted the retained contract."""


@dataclass(frozen=True)
class ContractStatus:
    label: str
    url: str
    status: str
    reason: str
    attempts: int
    evidence_sha256: str | None = None
    evidence_bytes: int | None = None
    authority_effect: str = "none"


def field_names(payload: dict[str, Any]) -> set[str]:
    return {
        str(field.get("name"))
        for field in payload.get("fields", [])
        if isinstance(field, dict) and field.get("name") is not None
    }


def validate_controlling(payload: dict[str, Any]) -> None:
    description = str(payload.get("description") or "")
    if "June 3rd 2025" not in description and "June 3, 2025" not in description:
        raise PopulatedMetadataDrift(
            f"controlling layer lost effective-date description: {description!r}"
        )
    if payload.get("geometryType") != "esriGeometryPolygon":
        raise PopulatedMetadataDrift(
            f"unexpected controlling geometry type: {payload.get('geometryType')!r}"
        )
    if "District_N" not in field_names(payload):
        raise PopulatedMetadataDrift("controlling layer lost District_N")


def validate_general(payload: dict[str, Any]) -> None:
    if "District_N" not in field_names(payload):
        raise PopulatedMetadataDrift("general layer lost District_N")


def validate_stale(payload: dict[str, Any]) -> None:
    text = " ".join(
        str(payload.get(key) or "")
        for key in ("serviceDescription", "description", "mapName", "name")
    )
    if "2010" not in text:
        raise PopulatedMetadataDrift(
            f"explicit 2010 stale-service marker is missing: {text!r}"
        )


def validate_controlling_html(text: str) -> None:
    lower = html.unescape(text).casefold()
    required_groups = (
        ("commissioner precinct",),
        ("esrigeometrypolygon", "esri geometry polygon"),
        ("district_n", "district n"),
        ("june 3rd 2025", "june 3, 2025"),
    )
    missing = [group for group in required_groups if not any(value in lower for value in group)]
    if missing:
        raise PopulatedMetadataDrift(
            "controlling HTML metadata lost required layer/date/field markers"
        )


def validate_general_html(text: str) -> None:
    lower = html.unescape(text).casefold()
    if "commissioner precinct" not in lower:
        raise PopulatedMetadataDrift("general HTML metadata lost layer identity")
    if "district_n" not in lower and "district n" not in lower:
        raise PopulatedMetadataDrift("general HTML metadata lost District_N")


def validate_stale_html(text: str) -> None:
    lower = html.unescape(text).casefold()
    if "2010" not in lower:
        raise PopulatedMetadataDrift(
            "stale-service HTML metadata lost the explicit 2010 marker"
        )


def json_contract_signals(payload: dict[str, Any]) -> bool:
    keys = {
        "name",
        "type",
        "description",
        "serviceDescription",
        "mapName",
        "geometryType",
        "fields",
        "objectIdField",
        "objectIdFieldName",
    }
    return any(key in payload for key in keys)


def parse_json_metadata(body: bytes, *, request_url: str) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = " ".join(body[:240].decode("utf-8", errors="replace").split())
        raise MetadataUnavailable(
            f"non-JSON response from {request_url}; preview={preview!r}"
        ) from exc
    if not isinstance(payload, dict):
        raise MetadataUnavailable(f"metadata response from {request_url} is not an object")
    if payload.get("error") is not None:
        raise MetadataUnavailable(
            f"ArcGIS error envelope from {request_url}: {payload['error']!r}"
        )
    if not payload or not json_contract_signals(payload):
        raise MetadataUnavailable(
            f"metadata response from {request_url} contains no layer contract signals"
        )
    return payload


def looks_like_generic_rest_shell(text: str) -> bool:
    lower = text.casefold()
    shell_markers = (
        "<!doctype html",
        "<html",
        "id=\"head1\"",
        "arcgis rest services directory",
        "/arcgis/rest",
        "rest/services",
        "esri",
    )
    layer_signals = (
        "district_n",
        "june 3rd 2025",
        "june 3, 2025",
        "commissioner precinct boundaries",
        "esrigeometrypolygon",
    )
    return (
        len(text.encode("utf-8")) <= 25_000
        and sum(marker in lower for marker in shell_markers) >= 2
        and not any(marker in lower for marker in layer_signals)
    )


def parse_html_metadata(
    body: bytes,
    *,
    request_url: str,
    validator: HtmlValidator,
) -> str:
    text = html.unescape(body.decode("utf-8", errors="replace"))
    if looks_like_generic_rest_shell(text):
        raise MetadataUnavailable(
            f"generic ArcGIS REST Directory shell from {request_url}"
        )
    validator(text)
    return text


def request_url(base_url: str, *, attempt: int, response_format: str | None) -> str:
    params = {"_cc_attempt": str(attempt)}
    if response_format is not None:
        params["f"] = response_format
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def fetch_contract(
    label: str,
    base_url: str,
    validator: Validator,
    html_validator: HtmlValidator,
    *,
    attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> ContractStatus:
    unavailable: list[str] = []
    drift: list[str] = []
    last_body: bytes | None = None

    for attempt in range(1, attempts + 1):
        for response_format in ("pjson", "json"):
            url = request_url(
                base_url,
                attempt=attempt,
                response_format=response_format,
            )
            request = urllib.request.Request(url, headers=HEADERS)
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    body = response.read()
                last_body = body
                payload = parse_json_metadata(body, request_url=url)
                validator(payload)
                return ContractStatus(
                    label=label,
                    url=base_url,
                    status="verified",
                    reason=f"validated populated ArcGIS {response_format} metadata",
                    attempts=attempt,
                    evidence_sha256=hashlib.sha256(body).hexdigest(),
                    evidence_bytes=len(body),
                )
            except MetadataUnavailable as exc:
                unavailable.append(
                    f"attempt={attempt} format={response_format}: {exc}"
                )
            except PopulatedMetadataDrift as exc:
                drift.append(
                    f"attempt={attempt} format={response_format}: {exc}"
                )
            except Exception as exc:
                unavailable.append(
                    f"attempt={attempt} format={response_format}: transport={exc!r}"
                )

        url = request_url(base_url, attempt=attempt, response_format=None)
        request = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
            last_body = body
            parse_html_metadata(body, request_url=url, validator=html_validator)
            return ContractStatus(
                label=label,
                url=base_url,
                status="verified",
                reason="validated populated ArcGIS HTML metadata",
                attempts=attempt,
                evidence_sha256=hashlib.sha256(body).hexdigest(),
                evidence_bytes=len(body),
            )
        except MetadataUnavailable as exc:
            unavailable.append(f"attempt={attempt} format=html: {exc}")
        except PopulatedMetadataDrift as exc:
            drift.append(f"attempt={attempt} format=html: {exc}")
        except Exception as exc:
            unavailable.append(
                f"attempt={attempt} format=html: transport={exc!r}"
            )

        if attempt < attempts:
            sleep(attempt * 5)

    if drift:
        raise SystemExit(
            f"Tarrant {label} metadata contract found populated drift after "
            f"{attempts} attempts: " + " | ".join(drift[-4:])
        )

    sha = hashlib.sha256(last_body).hexdigest() if last_body is not None else None
    size = len(last_body) if last_body is not None else None
    print(
        f"::warning::Tarrant {label} metadata unavailable after {attempts} "
        "bounded attempts; exact feature and snapshot checks remain blocking."
    )
    if unavailable:
        print("::notice::" + " | ".join(unavailable[-3:]))
    return ContractStatus(
        label=label,
        url=base_url,
        status="unavailable",
        reason=(
            "only empty/error/generic-shell/transport responses were observed; "
            "no metadata assertion was accepted"
        ),
        attempts=attempts,
        evidence_sha256=sha,
        evidence_bytes=size,
    )


def write_status(statuses: list[ContractStatus]) -> None:
    STATUS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "jurisdiction": "Tarrant County",
        "validation_scope": "ArcGIS metadata availability and hierarchy markers",
        "authority_effect": "none",
        "exact_feature_and_snapshot_checks_remain_blocking": True,
        "summary": {
            "verified": sum(item.status == "verified" for item in statuses),
            "unavailable": sum(item.status == "unavailable" for item in statuses),
        },
        "contracts": [asdict(item) for item in statuses],
    }
    STATUS_OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    specs = (
        (
            "controlling",
            URLS["controlling"],
            validate_controlling,
            validate_controlling_html,
        ),
        ("general", URLS["general"], validate_general, validate_general_html),
        ("stale_2010", URLS["stale_2010"], validate_stale, validate_stale_html),
    )
    statuses: list[ContractStatus] = []
    try:
        for label, url, validator, html_validator in specs:
            statuses.append(
                fetch_contract(label, url, validator, html_validator)
            )
    except BaseException:
        write_status(statuses)
        raise

    write_status(statuses)
    print(
        "Tarrant ArcGIS metadata hierarchy produced no contradictory populated "
        "response; exact geometry validation continues."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
