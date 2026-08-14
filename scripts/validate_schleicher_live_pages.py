#!/usr/bin/env python3
"""Validate current Schleicher County office pages with bounded contract retries."""

from __future__ import annotations

import hashlib
import html
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
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
EVIDENCE_DIR = Path("build/schleicher-county/live-pages")
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
    (
        "https://www.schleichercounty.gov/page/Treasurer",
        ("Cassandra Buitron",),
    ),
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
    )


def missing_markers(page: str, markers: tuple[str, ...]) -> list[str]:
    text = searchable(page)
    return [marker for marker in markers if searchable(marker) not in text]


def diagnostic(result: PageResult, missing: list[str]) -> str:
    body = result.text.encode("utf-8")
    preview = " ".join(result.text[:500].split())[:240]
    return (
        f"status={result.status}; content_type={result.content_type!r}; "
        f"bytes={len(body)}; sha256={hashlib.sha256(body).hexdigest()}; "
        f"missing={missing!r}; preview={preview!r}"
    )


def evidence_slug(url: str) -> str:
    path = urllib.parse.urlsplit(url).path.strip("/") or "homepage"
    return re.sub(r"[^a-z0-9]+", "-", path.casefold()).strip("-")


def retain_incomplete_page(
    url: str,
    attempt: int,
    result: PageResult,
    missing: list[str],
) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{evidence_slug(url)}-attempt-{attempt}"
    (EVIDENCE_DIR / f"{stem}.html").write_text(result.text, encoding="utf-8")
    (EVIDENCE_DIR / f"{stem}.txt").write_text(
        f"request_url={result.request_url}\n{diagnostic(result, missing)}\n",
        encoding="utf-8",
    )


def fetch_contract_page(
    url: str,
    markers: tuple[str, ...],
    *,
    attempts: int = 5,
) -> PageResult | None:
    """Return a page only after its marker contract passes.

    Unavailable pages retain the existing fail-soft behavior. Any HTTP-success
    body that is incomplete is retried with cache bypass, retained as evidence,
    and then fails closed with bounded diagnostics.
    """
    diagnostics: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            result = fetch_once(url, attempt)
        except Exception as exc:
            diagnostics.append(f"attempt={attempt}; transport_error={exc!r}")
        else:
            if result is None:
                return None
            missing = missing_markers(result.text, markers)
            if not missing:
                return result
            retain_incomplete_page(url, attempt, result, missing)
            diagnostics.append(
                f"attempt={attempt}; request_url={result.request_url!r}; "
                + diagnostic(result, missing)
            )
        if attempt < attempts:
            time.sleep(attempt * 3)

    raise SystemExit(
        f"{url} did not satisfy its live marker contract after {attempts} attempts: "
        + " | ".join(diagnostics[-3:])
    )


def main() -> int:
    accessible = 0
    for url, markers in CONTRACTS:
        page = fetch_contract_page(url, markers)
        accessible += page is not None
    print(f"Validated {accessible} live Schleicher County page contract(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
