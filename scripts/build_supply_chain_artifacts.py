#!/usr/bin/env python3
"""Build or verify the deterministic CycloneDX dependency inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-dev.lock"
DIRECT = ROOT / "requirements-dev.txt"
SBOM = ROOT / "sbom.cdx.json"
PACKAGE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")
HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})")


def normalize(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def parse_lock() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        match = PACKAGE.match(line)
        if match:
            if current:
                records.append(current)
            current = {
                "name": normalize(match.group(1)),
                "display_name": match.group(1),
                "version": match.group(2),
                "hashes": HASH.findall(line),
            }
        elif current:
            current["hashes"].extend(HASH.findall(line))
    if current:
        records.append(current)
    for record in records:
        record["hashes"] = sorted(set(record["hashes"]))
    if not records or any(not record["hashes"] for record in records):
        raise SystemExit("requirements-dev.lock is missing exact hashed package records")
    return records


def direct_names() -> set[str]:
    names: set[str] = set()
    for raw in DIRECT.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        names.add(normalize(re.split(r"[<>=!~ ]", line, 1)[0]))
    return names


def installed_distributions() -> dict[str, metadata.Distribution]:
    return {
        normalize(distribution.metadata.get("Name", "")): distribution
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }


def license_name(distribution: metadata.Distribution | None) -> str:
    if distribution is None:
        return "NOT RETAINED"
    value = (
        distribution.metadata.get("License-Expression")
        or distribution.metadata.get("License")
        or ""
    ).strip()
    if value and "\n" not in value and len(value) <= 180:
        return value
    classifiers = [
        item.removeprefix("License :: ").strip()
        for item in distribution.metadata.get_all("Classifier", [])
        if item.startswith("License :: ")
    ]
    return " OR ".join(classifiers) if classifiers else "SEE INSTALLED PACKAGE METADATA"


def component(record: dict[str, Any], direct: set[str], installed: dict[str, metadata.Distribution]) -> dict[str, Any]:
    name = record["name"]
    version = record["version"]
    distribution = installed.get(name)
    result: dict[str, Any] = {
        "type": "library",
        "bom-ref": f"pkg:pypi/{name}@{version}",
        "name": name,
        "version": version,
        "purl": f"pkg:pypi/{name}@{version}",
        "hashes": [
            {"alg": "SHA-256", "content": value}
            for value in record["hashes"]
        ],
        "licenses": [{"license": {"name": license_name(distribution)}}],
        "properties": [
            {"name": "civic-cartography:direct-dependency", "value": str(name in direct).lower()},
            {"name": "civic-cartography:retained-hash-count", "value": str(len(record["hashes"]))},
        ],
    }
    if distribution is not None:
        summary = (distribution.metadata.get("Summary") or "").strip()
        homepage = (distribution.metadata.get("Home-page") or "").strip()
        if summary:
            result["description"] = summary
        if homepage:
            result["externalReferences"] = [{"type": "website", "url": homepage}]
    return result


def build() -> str:
    lock_bytes = LOCK.read_bytes()
    lock_sha = hashlib.sha256(lock_bytes).hexdigest()
    records = parse_lock()
    direct = direct_names()
    installed = installed_distributions()
    names = {record["name"] for record in records}
    missing = sorted(names - set(installed))
    if missing:
        raise SystemExit(f"locked packages are not installed: {missing}")
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'civic-cartography:' + lock_sha)}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": "pkg:github/MightyLoud/Civic-Cartography",
                "name": "Civic-Cartography development and workflow environment",
            },
            "properties": [
                {"name": "civic-cartography:requirements-lock-sha256", "value": lock_sha},
                {"name": "civic-cartography:component-count", "value": str(len(records))},
            ],
        },
        "components": [component(record, direct, installed) for record in records],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    generated = build()
    if arguments.write:
        SBOM.write_text(generated, encoding="utf-8")
        print(f"wrote {SBOM.relative_to(ROOT)}")
        return 0
    if not SBOM.exists():
        raise SystemExit("sbom.cdx.json is missing")
    if SBOM.read_text(encoding="utf-8") != generated:
        raise SystemExit("sbom.cdx.json does not match the exact installed lock")
    print("CycloneDX SBOM matches the exact installed lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
