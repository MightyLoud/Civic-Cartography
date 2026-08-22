#!/usr/bin/env python3
"""Fail closed on mutable GitHub Actions or floating direct CI dependencies."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ALLOWED_ACTIONS = {
    "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
}
errors = []

for req in ("requirements-dev.txt", "requirements-ci.txt"):
    for number, raw in enumerate((ROOT / req).read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-r "):
            continue
        if "==" not in line or any(op in line for op in (">=", "<=", "~=", "!=", ">", "<")):
            errors.append(f"{req}:{number}: dependency is not exactly pinned: {line}")

for path in sorted(WORKFLOWS.glob("*.yml")):
    text = path.read_text()
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("uses:"):
            ref = stripped.split("uses:", 1)[1].split("#", 1)[0].strip()
            if ref.startswith("./"):
                continue
            if ref not in ALLOWED_ACTIONS:
                errors.append(f"{path}:{number}: unapproved or mutable action ref: {ref}")
        if re.search(r"\b(?:python -m )?pip install\b", stripped):
            direct_install = " -r requirements-ci.txt" in stripped
            locked_install = bool(re.fullmatch(
                r"run:\s+python -m pip install --require-hashes -r /tmp/requirements-ci\.generated\.lock",
                stripped,
            ))
            if not (direct_install or locked_install):
                errors.append(f"{path}:{number}: ad-hoc pip install: {stripped}")
        if "python-version:" in stripped and not re.search(r"python-version:\s*['\"]3\.12\.11['\"]", stripped):
            errors.append(f"{path}:{number}: Python runtime is not exactly 3.12.11")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"PASS: {len(list(WORKFLOWS.glob('*.yml')))} workflows use approved full-SHA actions and exact direct inputs")
