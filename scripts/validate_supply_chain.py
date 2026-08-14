#!/usr/bin/env python3
"""Fail closed when LIC-G5 supply-chain controls regress."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
LOCK = ROOT / "requirements-dev.lock"
DIRECT = ROOT / "requirements-dev.txt"
NOTICE = ROOT / "THIRD_PARTY_NOTICES.md"
SBOM = ROOT / "sbom.cdx.json"

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ACTION = re.compile(r"\buses:\s*([^@\s]+)@([^\s#]+)")
PINNED_OPENSTATES = "6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705"
ALLOWED_INSTALL = "python -m pip install --require-hashes -r requirements-dev.lock"


def package_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line and not line[0].isspace() and "==" in line and not line.startswith("#"):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def main() -> int:
    errors: list[str] = []
    required = [WORKFLOW_DIR, LOCK, DIRECT, NOTICE, SBOM]
    for path in required:
        if not path.exists():
            errors.append(f"missing required control: {path.relative_to(ROOT)}")
    if errors:
        raise SystemExit("\n".join(errors))

    workflow_text = ""
    for path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        workflow_text += "\n" + text
        for action, ref in ACTION.findall(text):
            if action.startswith("actions/") and not FULL_SHA.fullmatch(ref):
                errors.append(f"{path}: mutable GitHub Action reference {action}@{ref}")
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if "pip install" in stripped and ALLOWED_INSTALL not in stripped:
                errors.append(f"{path}:{number}: uncontrolled install: {stripped}")
            if "cache-dependency-path: requirements-dev.txt" in stripped:
                errors.append(f"{path}:{number}: cache still points to ranged manifest")
        if re.search(r"\b(?:pymupdf|fitz)\b", text, re.IGNORECASE):
            errors.append(f"{path}: PyMuPDF install/reference remains")

    direct_lines = [
        line.strip()
        for line in DIRECT.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    for line in direct_lines:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s;]+", line):
            errors.append(f"requirements-dev.txt is not exact: {line}")

    lock_text = LOCK.read_text(encoding="utf-8")
    blocks = package_blocks(lock_text)
    if not blocks:
        errors.append("requirements-dev.lock has no exact package records")
    for block in blocks:
        first = block.splitlines()[0]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s\\]+\s*\\?", first):
            errors.append(f"non-exact lock record: {first}")
        if "--hash=sha256:" not in block:
            errors.append(f"lock record has no integrity hash: {first}")
    if re.search(r"\b(?:pymupdf|fitz)\b", lock_text, re.IGNORECASE):
        errors.append("PyMuPDF remains in the exact lock")

    notice_text = NOTICE.read_text(encoding="utf-8")
    for marker in ("OpenStates", "AGPL", PINNED_OPENSTATES, "PyMuPDF"):
        if marker not in notice_text:
            errors.append(f"third-party notice missing marker: {marker}")

    try:
        sbom = json.loads(SBOM.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid CycloneDX SBOM: {exc}")
    else:
        components = sbom.get("components", [])
        if len(components) != len(blocks):
            errors.append(
                f"SBOM/lock mismatch: {len(components)} components, {len(blocks)} lock records"
            )
        names = {str(item.get("name", "")).lower() for item in components}
        if "pymupdf" in names:
            errors.append("PyMuPDF remains in the SBOM")

    if PINNED_OPENSTATES not in workflow_text:
        errors.append("pinned OpenStates revision is no longer retained")
    if "uv sync --frozen" not in workflow_text:
        errors.append("OpenStates frozen lock execution is no longer retained")

    if errors:
        print("LIC-G5 supply-chain controls: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "LIC-G5 supply-chain controls: PASS "
        f"({len(list(WORKFLOW_DIR.glob('*.y*ml')))} workflows; "
        f"{len(blocks)} hash-locked packages; "
        f"{len(sbom['components'])} SBOM components)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
