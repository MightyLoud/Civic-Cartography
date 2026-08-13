from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = ROOT / "evidence" / "measured-batch-100" / "closeout"
CANONICAL_REGISTER = ROOT / "evidence" / "measured-batch-100" / "completion-register.csv"
FROZEN_MAIN = "9440188ed766da8d9ec20f39ef781efad970a59c"
REGISTER_BLOB = "97514a9789545a3757e8908dec192becea1f99ec"
CERTIFICATION_COMMIT = "00ebd495ca5eee46f97e40f456622b3c696c97a1"
CERTIFICATION_BLOB = "4983d1b7f3633a0bcb75d868217dd1fe4b2a2ef9"
EXPECTED_IDS = [f"MB100-{n:03d}" for n in range(1, 101)]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DETERMINISTIC_FIELDS = (
    "resolved_ocdids",
    "match_status",
    "inferred_classification",
    "classification_status",
    "generation_status",
    "division_paths",
    "jurisdiction_paths",
    "exception_class",
    "review_reason",
    "output_hashes",
)


class CloseoutError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutError(message)


def read_csv(name: str) -> list[dict[str, str]]:
    path = CLOSEOUT / name
    require(path.is_file(), f"missing closeout artifact: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def index(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        target_id = row.get("target_id", "")
        require(target_id not in result, f"{label}: duplicate target_id {target_id}")
        result[target_id] = row
    return result


def target_number(target_id: str) -> int:
    return int(target_id.rsplit("-", 1)[1])


def truth(value: str) -> bool:
    return value.upper() == "TRUE"


def canonical_target_checksum(result: dict[str, Any]) -> str:
    paths = result.get("jurisdiction_paths") or []
    payload = {
        "canonical_ids": sorted(Path(path).stem for path in paths),
        "output_hashes": result.get("output_hashes") or {},
        "resolved_ocdids": result.get("resolved_ocdids") or [],
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_static() -> dict[str, Any]:
    freeze = json.loads((CLOSEOUT / "MB100_CLOSEOUT_FREEZE.json").read_text())
    require(freeze["frozen_main_commit"] == FROZEN_MAIN, "frozen main changed")
    require(
        freeze["completion_register_blob"] == REGISTER_BLOB,
        "completion-register blob changed",
    )
    require(freeze["certification"]["commit"] == CERTIFICATION_COMMIT, "certification commit changed")
    require(freeze["certification"]["blob"] == CERTIFICATION_BLOB, "certification blob changed")
    certification = json.loads(
        (ROOT / "evidence" / "measured-batch-100" / "certification.json").read_text()
    )
    require(certification["certification_decision_id"] == "D-094", "certification decision changed")
    require(
        certification["frozen_evidence"]["main_commit"] == FROZEN_MAIN,
        "certification frozen evidence changed",
    )
    require(
        certification["frozen_evidence"]["completion_register_blob"] == REGISTER_BLOB,
        "certification register blob changed",
    )
    require(
        certification["promotion"]["expansion_authorized"] is False,
        "certification authorized expansion",
    )
    require(freeze["contract"]["promotion_authorized"] is False, "promotion must remain false")
    require(
        freeze["contract"]["successor_decision_required"] is True,
        "successor decision must remain required",
    )

    manifest = read_csv("MB100_FINAL_MANIFEST.csv")
    results = read_csv("MB100_FINAL_RESULTS.csv")
    completion = read_csv("MB100_COMPLETION_REGISTER.csv")
    timers = read_csv("MB100_TIMER_RECONCILIATION.csv")
    routes = read_csv("MB100_EXCEPTION_TO_RULE_REGISTER.csv")
    archetypes = read_csv("MB100_ARCHETYPE_COVERAGE.csv")

    require([r["target_id"] for r in manifest] == EXPECTED_IDS, "manifest IDs/order differ")
    require([r["target_id"] for r in results] == EXPECTED_IDS, "result IDs/order differ")
    require([r["target_id"] for r in completion] == EXPECTED_IDS, "completion IDs/order differ")
    require(len({r["target_key"] for r in manifest}) == 100, "target keys are not unique")

    manifest_fields = (
        "target_id",
        "jurisdiction_name",
        "state",
        "target_type",
        "expected_archetype",
        "expected_classification",
        "row_role",
        "target_key",
        "source_identity",
        "selection_reason",
    )
    by_result = index(results, "results")
    for row in manifest:
        actual = by_result[row["target_id"]]
        for field in manifest_fields:
            require(actual[field] == row[field], f"{row['target_id']}: {field} drifted")

    require(all(r["outcome"] == "PASS" for r in results), "not all outcomes PASS")
    require(all(r["match_status"] == "MATCHED" for r in results), "not all targets matched")
    require(all(r["generation_status"] == "SUCCESS" for r in results), "not all generated")
    require(all(truth(r["parity_ok"]) for r in results), "parity has a false value")
    require(all(truth(r["portfolio_sync_ok"]) for r in results), "portfolio sync has a false value")
    require(all(truth(r["checksum_parity_ok"]) for r in results), "checksum parity false")
    for row in results:
        require(HEX64.fullmatch(row["checksum_run_1"]) is not None, f"{row['target_id']}: bad checksum 1")
        require(row["checksum_run_1"] == row["checksum_run_2"], f"{row['target_id']}: checksum mismatch")

    controls = [r for r in results if r["row_role"] == "REGRESSION CONTROL"]
    measured = [r for r in results if r["row_role"] != "REGRESSION CONTROL"]
    timer_true = [r for r in measured if truth(r["timer_integrity_ok"])]
    timer_false = [r for r in measured if r["timer_integrity_ok"] == "FALSE"]
    require(len(controls) == 6 and len(measured) == 94, "control/measured counts changed")
    require(len(timer_true) == 77 and len(timer_false) == 17, "strict timer count changed")
    for row in measured:
        for field in ("run_started_at", "run_stopped_at", "review_started_at", "review_stopped_at"):
            require(bool(row[field]), f"{row['target_id']}: missing {field}")

    canonical = index(read_csv_path(CANONICAL_REGISTER), "canonical register")
    by_completion = index(completion, "closeout completion")
    require(set(canonical) == set(EXPECTED_IDS[40:]), "canonical explicit coverage changed")
    require(sum(r["completion_mode"] == "LEGACY_PROXY" for r in completion) == 40, "legacy count changed")
    require(sum(r["completion_mode"] == "EXPLICIT" for r in completion) == 60, "explicit count changed")
    require(all(truth(r["effective_complete_ok"]) for r in completion), "effective completion false")
    explicit_compare = (
        "evaluation_id",
        "raw_exists",
        "normalized_exists",
        "identifier_join_ok",
        "qa_ok",
        "parity_ok",
        "source_provenance_ok",
        "complete_ok",
        "confidence",
        "failed_gates",
        "source_manifest_sha256",
        "manifest_sha256",
        "first_run_id",
        "second_run_id",
        "run_asof",
    )
    for target_id in EXPECTED_IDS:
        row = by_completion[target_id]
        number = target_number(target_id)
        require(int(row["target_num"]) == number, f"{target_id}: target_num drifted")
        if number <= 40:
            require(row["completion_mode"] == "LEGACY_PROXY", f"{target_id}: legacy mode drifted")
            require(truth(row["legacy_proxy_ok"]), f"{target_id}: legacy proxy false")
            require(not truth(row["explicit_record_found"]), f"{target_id}: unexpected explicit record")
            require(not truth(row["explicit_complete_ok"]), f"{target_id}: unexpected explicit complete")
            require(
                all(
                    not row[field]
                    for field in (
                        "explicit_evidence_ref",
                        "explicit_jurisdiction_name",
                        "explicit_state",
                        *explicit_compare,
                    )
                ),
                f"{target_id}: fabricated explicit evidence",
            )
        else:
            require(row["completion_mode"] == "EXPLICIT", f"{target_id}: explicit mode drifted")
            require(truth(row["explicit_record_found"]), f"{target_id}: explicit record missing")
            require(truth(row["explicit_complete_ok"]), f"{target_id}: explicit complete false")
            source = canonical[target_id]
            require(row["explicit_jurisdiction_name"] == source["jurisdiction_name"], f"{target_id}: explicit name differs")
            require(row["explicit_state"].lower() == source["state"].lower(), f"{target_id}: explicit state differs")
            require(
                row["explicit_evidence_ref"] == source["evidence_ref"],
                f"{target_id}: explicit evidence_ref differs",
            )
            for field in explicit_compare:
                require(row[field] == source[field], f"{target_id}: {field} differs from canonical register")

    checksum_rows: dict[str, dict[str, str]] = {}
    checksum_path = CLOSEOUT / "MB100_CHECKSUMS.sha256"
    lines = [
        line for line in checksum_path.read_text().splitlines()
        if line and not line.startswith("#")
    ]
    require(len(lines) == 200, "checksum declaration must contain 200 run lines")
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (MB100-[0-9]{3})/run-([12])", line)
        require(match is not None, f"bad checksum declaration: {line}")
        digest, target_id, run_number = match.groups()
        checksum_rows.setdefault(target_id, {})[run_number] = digest
    require(sorted(checksum_rows) == EXPECTED_IDS, "checksum target coverage differs")
    for target_id, declared in checksum_rows.items():
        row = by_result[target_id]
        require(declared == {"1": row["checksum_run_1"], "2": row["checksum_run_2"]}, f"{target_id}: checksum file drifted")

    require(len(timers) == 19, "timer reconciliation must contain 19 records")
    false_ids = {r["target_id"] for r in timer_false}
    preserved_false = {r["target_id"] for r in timers if r["source_timer_integrity"] == "FALSE"}
    require(preserved_false == false_ids, "historical strict timer exceptions differ")
    conflicts = [r for r in timers if r["defect_class"].startswith("DECISION_SOURCE_CONFLICT")]
    require({r["target_id"] for r in conflicts} == {"MB100-041", "MB100-051"}, "timer conflicts differ")
    for row in timers:
        source = by_result[row["target_id"]]
        for closeout_field, result_field in (
            ("run_started_at", "run_started_at"),
            ("run_stopped_at", "run_stopped_at"),
            ("review_started_at", "review_started_at"),
            ("review_stopped_at", "review_stopped_at"),
        ):
            require(row[closeout_field] == source[result_field], f"{row['target_id']}: timestamp changed")
        require(row["successor_decision"] == "", f"{row['target_id']}: premature successor decision")
        require(row["effective_gate"].startswith("WAIT"), f"{row['target_id']}: timer gate forced")
    require(not (CLOSEOUT / "MB100_PROMOTION_DECISION.json").exists(), "promotion decision must be absent")

    discovery_ids = {r["target_id"] for r in results if r["row_role"] == "MEASURED — DISCOVERY"}
    require(len(routes) == 8, "discovery route count changed")
    require({r["target_id"] for r in routes} == discovery_ids, "discovery route coverage differs")
    require(all(r["outcome"] == "PASS" and r["unrouted"] == "FALSE" for r in routes), "unrouted discovery")

    require(len(archetypes) == 7, "archetype count changed")
    require(
        {r["archetype_id"] for r in archetypes}
        == {"AR-001", "AR-002", "AR-003", "AR-004", "AR-005", "AR-D01", "AR-D02"},
        "archetype IDs changed",
    )
    require(sum(int(r["mb100_routed_target_count"]) for r in archetypes) == 100, "archetype coverage not 100")
    require(sum(int(r["active_fixture_count"]) for r in archetypes) == 6, "active fixture count changed")
    require(sum(int(r["staged_fixture_count"]) for r in archetypes) == 2, "staged fixture count changed")
    require((CLOSEOUT / "MB100_CLOSEOUT_REPORT.md").is_file(), "closeout report missing")

    yaml_manifest = yaml.safe_load((CLOSEOUT / "MB100_FINAL_MANIFEST.yml").read_text())
    require(yaml_manifest["version"] == 1 and len(yaml_manifest["targets"]) == 100, "YAML manifest invalid")
    yaml_by_id = {r["target_id"]: r for r in yaml_manifest["targets"]}
    require(list(yaml_by_id) == EXPECTED_IDS, "YAML manifest order/IDs differ")
    for row in manifest:
        y = yaml_by_id[row["target_id"]]
        selector = y["selector"]
        key = (
            f"lookup:{selector['name']}"
            if selector["type"] == "explicit_lookup"
            else selector["value"]
        )
        require(key == row["target_key"], f"{row['target_id']}: YAML selector differs")
        require(y["jurisdiction_name"] == row["jurisdiction_name"], f"{row['target_id']}: YAML name differs")
        require(y["state"] == row["state"].lower(), f"{row['target_id']}: YAML state differs")
        require(y["expected_archetype"] == row["expected_archetype"], f"{row['target_id']}: YAML archetype differs")
        require(y["expected_classification"] == row["expected_classification"], f"{row['target_id']}: YAML class differs")

    return {
        "target_count": 100,
        "pass_count": 100,
        "checksum_parity_count": 100,
        "completion": {"effective": 100, "explicit": 60, "legacy_proxy": 40},
        "timers": {"strict_true": 77, "measured": 94, "historical_false": 17, "decision_source_conflicts": 2},
        "discoveries_routed": 8,
        "archetypes": 7,
        "active_fixtures": 6,
        "staged_fixtures": 2,
        "promotion_gates": "7/8",
    }


def read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_rerun(
    first_path: Path,
    second_path: Path,
    completion_path: Path,
    fixture_path: Path,
) -> dict[str, Any]:
    first = json.loads(first_path.read_text())
    second = json.loads(second_path.read_text())
    require(first == second, "clean rerun reports are not byte-semantic identical")
    require(first["run_asof"] == "2026-08-13T01:42:43Z", "rerun as-of changed")
    require(first["summary"]["target_count"] == 100, "rerun target count changed")
    first_by_id = {r["target_id"]: r for r in first["results"]}
    require(sorted(first_by_id) == EXPECTED_IDS, "rerun result coverage differs")

    frozen = index(read_csv("MB100_FINAL_RESULTS.csv"), "frozen results")
    for target_id in EXPECTED_IDS:
        actual = first_by_id[target_id]
        expected = frozen[target_id]
        require(actual.get("match_status") in {"matched", "resolved"}, f"{target_id}: rerun unresolved")
        require(actual.get("classification_status") == "matched", f"{target_id}: rerun classification mismatch")
        require(actual.get("generation_status") == "generated", f"{target_id}: rerun generation failed")
        require(actual.get("inferred_classification") == expected["expected_classification"], f"{target_id}: class drifted")
        require(actual.get("exception_class") is None, f"{target_id}: rerun exception remains")
        for field in DETERMINISTIC_FIELDS:
            require(actual.get(field) == second["results"][EXPECTED_IDS.index(target_id)].get(field), f"{target_id}: {field} nondeterministic")
        checksum = canonical_target_checksum(actual)
        require(checksum == expected["checksum_run_1"], f"{target_id}: frozen checksum mismatch")

    completion = json.loads(completion_path.read_text())
    require(completion["summary"]["target_count"] == 100, "rerun completion target count changed")
    require(completion["summary"]["complete_count"] == 100, "rerun not 100/100 complete")
    require(completion["summary"]["all_complete"] is True, "rerun completion gate false")
    require(all(r["complete_ok"] is True for r in completion["targets"]), "rerun has incomplete target")

    fixtures = json.loads(fixture_path.read_text())
    summary = fixtures["summary"]
    require(summary["fixture_count"] == 6, "active fixture count changed")
    require(summary["passed_count"] == 6, "active fixture failure")
    require(summary["deterministic_count"] == 6, "fixture nondeterminism")
    require(summary["report_content_match"] is True, "fixture reports differ")
    require(summary["gate_passed"] is True, "fixture gate false")

    return {
        "run_asof": first["run_asof"],
        "manifest_sha256": first["manifest_sha256"],
        "first_run_id": first["run_id"],
        "second_run_id": second["run_id"],
        "target_count": 100,
        "complete_count": 100,
        "checksum_match_count": 100,
        "command_parity": True,
        "active_fixture_summary": summary,
        "staged_fixture_activation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the frozen MB100 closeout package.")
    parser.add_argument("--first-report", type=Path)
    parser.add_argument("--second-report", type=Path)
    parser.add_argument("--completion-manifest", type=Path)
    parser.add_argument("--fixture-evaluation", type=Path)
    parser.add_argument("--evidence-json", type=Path)
    args = parser.parse_args()
    supplied = [
        args.first_report,
        args.second_report,
        args.completion_manifest,
        args.fixture_evaluation,
    ]
    try:
        static = validate_static()
        rerun = None
        if any(supplied):
            require(all(supplied), "all rerun evidence paths must be supplied together")
            rerun = validate_rerun(*supplied)
        if args.evidence_json:
            require(rerun is not None, "evidence JSON requires rerun inputs")
            evidence = {
                "schema_version": 1,
                "status": "PASS",
                "candidate": {
                    "repository": os.environ.get("GITHUB_REPOSITORY", ""),
                    "sha": os.environ.get("GITHUB_SHA", ""),
                    "run_id": os.environ.get("GITHUB_RUN_ID", ""),
                    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
                },
                "frozen_main_commit": FROZEN_MAIN,
                "completion_register_blob": REGISTER_BLOB,
                "certification_commit": CERTIFICATION_COMMIT,
                "certification_blob": CERTIFICATION_BLOB,
                "static_closeout": static,
                "clean_rerun": rerun,
                "repository_tests": os.environ.get("MB100_REPO_TESTS", "NOT_RECORDED"),
                "historical_timer_integrity": "77/94",
                "promotion_gates": "7/8",
                "promotion_authorized": False,
                "successor_decision_required": True,
            }
            args.evidence_json.parent.mkdir(parents=True, exist_ok=True)
            args.evidence_json.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(
            "MB100 closeout: 100/100 static PASS"
            + ("; 100/100 clean rerun PASS" if rerun else "")
            + "; promotion HOLD"
        )
    except (CloseoutError, KeyError, OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"MB100 closeout validation failed: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
