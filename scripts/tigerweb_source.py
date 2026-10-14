"""Read TIGERweb vintage metadata without guessing from a moving service URL."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable
from urllib.request import Request, urlopen

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def fetch_source_vintage(layer_url: str) -> str:
    request = Request(
        f"{layer_url}?f=json",
        headers={"User-Agent": "Civic-Cartography/0.1"},
    )
    with urlopen(request, timeout=60) as response:
        metadata = json.load(response)
    if not isinstance(metadata, dict) or metadata.get("error"):
        raise ValueError("TIGERweb layer metadata is missing or reports an error")
    description = metadata.get("description")
    match = re.search(
        rf";\s*({'|'.join(MONTHS)}) ([0-9]{{1,2}}), ([0-9]{{4}}) vintage\s*$",
        description if isinstance(description, str) else "",
    )
    if match is None:
        raise ValueError("TIGERweb layer metadata has no recognized source vintage")
    month, day, year = match.groups()
    return date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()


def fetch_with_vintage(
    layer_url: str, fetch: Callable[[], tuple[dict, str]],
) -> tuple[dict, str, str]:
    """Reject a vintage rollover during a fetch before any output is written."""
    vintage = fetch_source_vintage(layer_url)
    payload, request_url = fetch()
    if fetch_source_vintage(layer_url) != vintage:
        raise ValueError("TIGERweb source vintage changed during the fetch; retry")
    return payload, request_url, vintage
