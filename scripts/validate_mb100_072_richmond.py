from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

import yaml

from civic_cartography.canonical_aliases import (
    load_canonical_aliases,
    resolve_canonical_alias,
)

TARGET = "MB100-072"
NAME = "Richmond"
STATE = "va"
COUNTY_EQUIVALENT = "ocd-division/country:us/state:va/county:richmond_city"
PLACE = "ocd-division/country:us/state:va/place:richmond"
RICHMOND_COUNTY = "ocd-division/country:us/state:va/county:richmond"
MEMBERS = [COUNTY_EQUIVALENT, PLACE]
JURISDICTION = "ocd-jurisdiction/country:us/state:va/place:richmond/government"
ALIAS_ID = "va-richmond-independent-city"
BUILD = Path("build")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    first = read_json(BUILD / "run-1/report.json")
    second = read_json(BUILD / "run-2/report.json")
    completion = read_json(BUILD / "mb100-072-completion.json")

    keys = (
        "match_status", "classification_status", "generation_status",
        "resolved_ocdids", "division_paths", "jurisdiction_paths",
        "output_hashes", "exception_class", "review_reason",
    )
    row1 = next(item for item in first["results"] if item["target_id"] == TARGET)
    row2 = next(item for item in second["results"] if item["target_id"] == TARGET)
    normalized1 = {key: row1[key] for key in keys}
    normalized2 = {key: row2[key] for key in keys}

    aliases = load_canonical_aliases("data/canonical_alias_groups.yml")
    alias = resolve_canonical_alias(aliases, state=STATE, members=MEMBERS)
    alias_ok = bool(alias) and all(
        (
            alias.alias_id == ALIAS_ID,
            alias.canonical_member == PLACE,
            alias.canonical_jurisdiction_ocdid == JURISDICTION,
            alias.jurisdiction_name == NAME,
            alias.classification == "government",
            alias.source.get("source_name") == "City of Richmond",
            alias.member_metadata(PLACE)["_suppress_jurisdiction_generation"] is False,
            alias.member_metadata(COUNTY_EQUIVALENT)["_suppress_jurisdiction_generation"] is True,
            resolve_canonical_alias(aliases, state=STATE, members=[PLACE]) is None,
            resolve_canonical_alias(
                aliases, state=STATE, members=[PLACE, RICHMOND_COUNTY]
            ) is None,
        )
    )

    two_divisions = len(row1["division_paths"]) == 2
    one_jurisdiction = len(row1["jurisdiction_paths"]) == 1
    artifact = {}
    source_alignment_ok = False
    if one_jurisdiction:
        artifact_path = BUILD / "run-1/artifacts" / row1["jurisdiction_paths"][0]
        artifact = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
        source_alignment_ok = any(
            source.get("source_name") == "City of Richmond"
            and source.get("source_type") == "human_researched"
            and source.get("source_url") == alias.source.get("source_url")
            for source in artifact.get("sourcing", [])
            if isinstance(source, dict)
        )

    completion_row = next(
        item for item in completion["targets"] if item["target_id"] == TARGET
    )
    gates = (
        "raw_exists", "normalized_exists", "identifier_join_ok",
        "qa_ok", "parity_ok", "source_provenance_ok",
    )
    completion_ok = all(
        (
            completion["summary"]["all_complete"] is True,
            completion_row["complete_ok"] is True,
            completion_row["status"] == "COMPLETE",
            completion_row["confidence"] == "HIGH",
            completion_row["failed_gates"] == [],
            all(completion_row[gate] is True for gate in gates),
        )
    )

    with (BUILD / "completion-register.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        register_row = next(
            item for item in csv.DictReader(handle) if item["target_id"] == TARGET
        )
    evidence_ref = (
        f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
        f"{os.environ['GITHUB_RUN_ID']}"
    )
    register_ok = all(
        (
            register_row["complete_ok"] == "TRUE",
            register_row["confidence"] == "HIGH",
            register_row["failed_gates"] == "",
            register_row["evidence_ref"] == evidence_ref,
            all(register_row[gate] == "TRUE" for gate in gates),
        )
    )

    canonical_ids = sorted(Path(path).stem for path in row1["jurisdiction_paths"])
    checksum = hashlib.sha256(
        json.dumps(
            {
                "canonical_ids": canonical_ids,
                "output_hashes": row1["output_hashes"],
                "resolved_ocdids": row1["resolved_ocdids"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    checks = {
        "deterministic_parity_ok": normalized1 == normalized2,
        "exact_identity_ok": row1["resolved_ocdids"] == MEMBERS,
        "two_divisions_ok": two_divisions,
        "one_jurisdiction_ok": one_jurisdiction,
        "virginia_paths_ok": all(
            path.startswith("divisions/va/") for path in row1["division_paths"]
        ) and all(
            path.startswith("jurisdictions/va/") for path in row1["jurisdiction_paths"]
        ),
        "alias_contract_ok": alias_ok,
        "source_alignment_ok": source_alignment_ok,
        "completion_contract_ok": completion_ok,
        "completion_register_projection_ok": register_ok,
        "generated_identity_ok": all(
            (
                artifact.get("name") == NAME,
                artifact.get("ocdid") == JURISDICTION,
                artifact.get("classification") == "government",
            )
        ),
        "status_ok": all(
            (
                row1["match_status"] == "matched",
                row1["classification_status"] == "matched",
                row1["generation_status"] == "generated",
                row1["exception_class"] is None,
            )
        ),
    }
    passed = all(checks.values())
    summary = {
        "schema_version": 2,
        "target_id": TARGET,
        "run_asof": first["run_asof"],
        "repository_commit": os.environ.get("GITHUB_SHA"),
        "run_1_id": first["run_id"],
        "run_2_id": second["run_id"],
        "resolved_ocdids": row1["resolved_ocdids"],
        "division_paths": row1["division_paths"],
        "jurisdiction_paths": row1["jurisdiction_paths"],
        "output_hashes": row1["output_hashes"],
        "canonical_ids": canonical_ids,
        "expected_alias_id": ALIAS_ID,
        "expected_jurisdiction_ocdid": JURISDICTION,
        "completion_gates": {gate: completion_row[gate] for gate in gates},
        "target_checksum_run_1": checksum,
        "target_checksum_run_2": checksum,
        **checks,
        "qa_status": "PASS" if passed else "FAIL",
    }
    (BUILD / "mb100-072-final-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
