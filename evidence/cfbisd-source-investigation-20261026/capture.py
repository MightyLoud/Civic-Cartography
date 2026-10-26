"""Capture CFBISD evidence into a NEW directory; never update approved data.

Run from the repository root:
    python evidence/cfbisd-source-investigation-20261026/capture.py NEW_DIRECTORY
Only Python's standard library and existing repository code are required.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.fetch_tigerweb_school_district import LAYER_URL, canonicalize, write_json
from scripts.tigerweb_source import MONTHS


def capture(destination: Path) -> None:
    # An existing folder is an error, even if it is empty.
    destination.mkdir(parents=True, exist_ok=False)
    baseline_path = ROOT / "data/geojson/carrollton_farmers_branch_isd_districtwide.geojson"
    baseline = json.loads(baseline_path.read_text())["features"][0]["properties"]
    request_url = baseline["source_request_url"]
    manifest = {"captures": [], "baseline_replacement_approved": False}

    def get(url: str, path: Path) -> dict:
        started = datetime.now(timezone.utc).isoformat()
        request = Request(url, headers={"User-Agent": "Civic-Cartography/0.1"})
        with urlopen(request, timeout=60) as response:
            body = response.read()
            headers = {k: response.headers.get(k) for k in ("Date", "ETag", "Last-Modified")}
        # Preserve actual server response bytes, not a JSON reserialization.
        path.write_bytes(body)
        return {
            "url": url, "file": path.name, "sha256": hashlib.sha256(body).hexdigest(),
            "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "response_headers": headers,
        }

    def vintage(path: Path) -> str:
        import re
        metadata = json.loads(path.read_bytes())
        if metadata.get("error") or metadata.get("name") != "Unified School Districts":
            raise ValueError("Unexpected Census school-district metadata")
        match = re.search(r"; (\w+) (\d+), (\d+) vintage$", metadata["description"])
        if not match:
            raise ValueError("Missing official source vintage")
        month, day, year = match.groups()
        from datetime import date
        return date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()

    for number in (1, 2):
        prefix = f"capture-{number}"
        before = destination / f"{prefix}-metadata-before.json"
        raw = destination / f"{prefix}-raw.geojson"
        after = destination / f"{prefix}-metadata-after.json"
        records = [get(f"{LAYER_URL}?f=json", before)]
        records.append(get(request_url, raw))
        records.append(get(f"{LAYER_URL}?f=json", after))
        source_vintage = vintage(before)
        if source_vintage != vintage(after):
            raise ValueError("Census vintage changed during capture; preserve partial evidence and retry in a new folder")
        payload = json.loads(raw.read_bytes())
        if payload.get("type") != "FeatureCollection" or len(payload.get("features", [])) != 1:
            raise ValueError("Expected exactly one Census feature")
        properties = payload["features"][0]["properties"]
        if properties.get("GEOID") != "4813050" or properties.get("BASENAME") != baseline["jurisdiction_name"]:
            raise ValueError("Unexpected Census district identity")
        canonical = canonicalize(
            payload, record_id=baseline["record_id"], geometry_id=baseline["geometry_id"],
            retrieved_at=records[1]["finished_at_utc"][:10], request_url=request_url,
            source_vintage=source_vintage,
        )
        candidate = destination / f"{prefix}-candidate.geojson"
        write_json(candidate, canonical)
        manifest["captures"].append({
            "number": number, "source_vintage": source_vintage, "requests": records,
            "candidate_file": candidate.name,
            "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        })
        print(f"Preserved capture {number}; GEOID 4813050; vintage {source_vintage}", flush=True)
    write_json(destination / "capture-manifest.json", manifest)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Supply a new output directory")
    capture(Path(sys.argv[1]))
