#!/usr/bin/env python3
"""Validate current Schleicher County pages without treating a transport shell as data.

Committed roster, scope, geometry, QA, and digest checks remain separate and blocking.
This validator preserves the historical fail-soft behavior for genuinely unavailable
pages.  A successful HTTP response that contains populated, contradictory page
content still fails closed.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
}
STATUS_OUTPUT = Path("build/schleicher-county/live-page-status.json")
TREASURER_URL = "https://www.schleichercounty.gov/page/Treasurer"
CONTRACTS = [
    (
        "https://www.schleichercounty.gov/page/homepage",
        ("Charlie Bradley", "Gary Gibson", "Steve Nelson", "Kirk Griffin", "Chris Meador"),
    ),
    (
        "https://www.schleichercounty.gov/page/Commissioner.Court",
        ("Gary Gibson", "Steve Nelson", "Kirk Griffin", "Chris Meador"),
    ),
    ("https://www.schleichercounty.gov/page/County.Judge", ("Charlie Bradley",)),
    ("https://www.schleichercounty.gov/page/Sheriff", ("Jason Chatham",)),
    (
        "https://www.schleichercounty.gov/page/County.Clerk",
        ("Marsha L. Maskill", "County and District Clerk"),
    ),
    (
        "https://www.schleichercounty.gov/page/District.Clerk",
        ("Marsha L. Maskill", "County and District Clerk"),
    ),
    (
        "https://www.schleichercounty.gov/page/Elections",
        ("Marsha L. Maskill", "Precincts 1, 2, 3, 4"),
    ),
    (
        "https://www.schleichercounty.gov/page/Tax.Assessor",
        ("Vanessa Covarrubiaz",),
    ),
    (TREASURER_URL, ("Jennifer L. Henderson",)),
    (
        "https://www.schleichercounty.gov/page/countyattorney",
        ("Clint T. Griffin",),
    ),
]


@dataclass(frozen=True)
class PageResult:
    text: str
    request_url: str
    status: int
    content_type: str
    body_sha256: str
    body_bytes: int


@dataclass(frozen=True)
class ContractStatus:
    url: str
    status: str
    reason: str
    attempts: int
    missing_markers: tuple[str, ...] = ()
    request_url: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    body_sha256: str | None = None
    body_bytes: int | None = None
    authority_effect: str = "none"


def searchable(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def cache_busted_url(url: str, attempt: int) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.extend(
        [
            ("_cc_contract_attempt", str(attempt)),
            ("_cc_contract_transport", "html"),
        ]
    )
    return urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urllib.parse.urlencode(query),
            parts.fragment,
        )
    )


def fetch_once(url: str, attempt: int) -> PageResult | None:
    request_url = cache_busted_url(url, attempt)
    request = urllib.request.Request(request_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read()
            status = int(getattr(response, "status", response.getcode()))
            content_type = str(response.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404, 429}:
            return None
        raise

    return PageResult(
        text=html.unescape(body.decode("utf-8", errors="replace")),
        request_url=request_url,
        status=status,
        content_type=content_type,
        body_sha256=hashlib.sha256(body).hexdigest(),
        body_bytes=len(body),
    )


def missing_markers(page: str, markers: tuple[str, ...]) -> list[str]:
    text = searchable(page)
    return [marker for marker in markers if searchable(marker) not in text]


def is_content_free_civicweb_shell(result: PageResult) -> bool:
    """Recognize only the generic CivicWeb bootstrap returned for Treasurer.

    The classifier is intentionally narrow.  It requires multiple framework
    fingerprints and no office-specific contact/content signal.  A populated
    Treasurer page that merely changes the retained officeholder therefore does
    not qualify and remains a hard contract failure.
    """
    lower = result.text.casefold()
    shell_markers = (
        "/runtime/images/favicon.ico",
        "__viewstate",
        "__eventvalidation",
        "webresource.axd",
        "scriptresource.axd",
        "<form",
        "content-type\" content=\"text/html",
    )
    shell_score = sum(marker in lower for marker in shell_markers)
    office_content_signals = (
        "jennifer l. henderson",
        "jennifer henderson",
        "mailto:",
        "@schleichercounty",
        "physical address",
        "mailing address",
        "office hours",
        "phone:",
        "fax:",
    )
    has_office_content = any(signal in lower for signal in office_content_signals)
    return (
        result.status == 200
        and "html" in result.content_type.casefold()
        and result.body_bytes <= 100_000
        and shell_score >= 3
        and not has_office_content
    )


def status_from_result(
    *,
    url: str,
    status: str,
    reason: str,
    attempts: int,
    result: PageResult | None,
    missing: tuple[str, ...] = (),
) -> ContractStatus:
    return ContractStatus(
        url=url,
        status=status,
        reason=reason,
        attempts=attempts,
        missing_markers=missing,
        request_url=result.request_url if result else None,
        http_status=result.status if result else None,
        content_type=result.content_type if result else None,
        body_sha256=result.body_sha256 if result else None,
        body_bytes=result.body_bytes if result else None,
    )


def validate_contract(
    url: str,
    markers: tuple[str, ...],
    *,
    attempts: int = 5,
    sleep: callable = time.sleep,
) -> ContractStatus:
    diagnostics: list[str] = []
    last_result: PageResult | None = None
    last_missing: tuple[str, ...] = ()
    transport_only = True

    for attempt in range(1, attempts + 1):
        try:
            result = fetch_once(url, attempt)
        except Exception as exc:
            diagnostics.append(f"attempt={attempt}; transport_error={exc!r}")
        else:
            if result is None:
                return status_from_result(
                    url=url,
                    status="unavailable",
                    reason="official page returned an unavailable HTTP status",
                    attempts=attempt,
                    result=None,
                )

            last_result = result
            missing = tuple(missing_markers(result.text, markers))
            last_missing = missing
            if not missing:
                return status_from_result(
                    url=url,
                    status="verified",
                    reason="all retained live markers are present",
                    attempts=attempt,
                    result=result,
                )

            transport_only = False
            if url == TREASURER_URL and is_content_free_civicweb_shell(result):
                diagnostics.append(
                    f"attempt={attempt}; recognized content-free CivicWeb shell; "
                    f"sha256={result.body_sha256}; missing={list(missing)!r}"
                )
            else:
                preview = " ".join(result.text[:500].split())[:240]
                diagnostics.append(
                    f"attempt={attempt}; populated HTTP response lost markers "
                    f"{list(missing)!r}; status={result.status}; "
                    f"content_type={result.content_type!r}; bytes={result.body_bytes}; "
                    f"sha256={result.body_sha256}; preview={preview!r}"
                )
                if attempt == attempts:
                    raise SystemExit(
                        f"{url} did not satisfy its live marker contract after "
                        f"{attempts} attempts: " + " | ".join(diagnostics[-3:])
                    )

        if attempt < attempts:
            sleep(attempt * 3)

    if (
        url == TREASURER_URL
        and last_result is not None
        and last_missing
        and is_content_free_civicweb_shell(last_result)
    ):
        return status_from_result(
            url=url,
            status="unavailable",
            reason=(
                "official Treasurer route repeatedly returned the generic "
                "content-free CivicWeb shell; no officeholder assertion was read"
            ),
            attempts=attempts,
            result=last_result,
            missing=last_missing,
        )

    if transport_only:
        return status_from_result(
            url=url,
            status="unavailable",
            reason="all bounded attempts ended in transport unavailability",
            attempts=attempts,
            result=last_result,
            missing=last_missing,
        )

    raise SystemExit(
        f"{url} did not satisfy its live marker contract after {attempts} attempts: "
        + " | ".join(diagnostics[-3:])
    )


def write_status(statuses: list[ContractStatus]) -> None:
    STATUS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "jurisdiction": "Schleicher County",
        "validation_scope": "live-page availability and retained marker checks",
        "authority_effect": "none",
        "committed_release_contract_remains_controlling": True,
        "summary": {
            "verified": sum(item.status == "verified" for item in statuses),
            "unavailable": sum(item.status == "unavailable" for item in statuses),
            "failed": sum(item.status == "failed" for item in statuses),
        },
        "contracts": [asdict(item) for item in statuses],
    }
    STATUS_OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    statuses: list[ContractStatus] = []
    try:
        for url, markers in CONTRACTS:
            statuses.append(validate_contract(url, markers))
    except BaseException:
        write_status(statuses)
        raise

    write_status(statuses)
    verified = sum(item.status == "verified" for item in statuses)
    unavailable = sum(item.status == "unavailable" for item in statuses)
    print(
        f"Schleicher live-page contracts: {verified} verified, "
        f"{unavailable} unavailable, zero contradictory populated pages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
