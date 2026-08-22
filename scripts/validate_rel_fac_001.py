#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/rel_fac_001_cases.json")
SCHEMA = Path("schemas/rel-fac-report.schema.json")
QA_MATRIX = Path("tests/fixtures/qa_fac_001_outcome_matrix.json")
QA_SCRIPT = Path("scripts/validate_qa_fac_001.py")


def canonical_hash(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_qa_module():
    spec = importlib.util.spec_from_file_location("qa_fac_001", QA_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_status(checks):
    statuses = [row["status"] for row in checks]
    return "FAIL" if "FAIL" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS"


def exception_from_check(case, check, blocking):
    return {
        "exception_id": f"{case['case_id']}-{check['check_id'].lower()}",
        "factory": case.get("factory", "REL-FAC"),
        "gate_id": case["gate_id"],
        "entity_type": None,
        "entity_id": None,
        "exception_type": "QA_CHECK_" + check["status"],
        "severity": "ERROR" if blocking else "REVIEW",
        "blocking": blocking,
        "status": "OPEN" if blocking else "QUEUED",
        "owner": None,
        "source_id": None,
        "description": check["detail"],
        "resolution": None,
    }


def normalized_input(case, qa_reports):
    if case["source_mode"] == "qa_gate":
        qa = qa_reports[case["qa_gate_id"]]
        checks = [
            {"check_id": check_id, "status": row["status"], "detail": row["detail"]}
            for check_id, row in sorted(qa["checks"].items())
        ]
        exceptions = []
        if qa["gate_id"] == "GEO-FAC-001":
            q07 = next(row for row in checks if row["check_id"] == "Q07")
            exceptions.append({
                "exception_id": "geo-local-layer-unresolved",
                "factory": "GEO-FAC",
                "gate_id": qa["gate_id"],
                "entity_type": "Division",
                "entity_id": None,
                "exception_type": "LOCAL_LAYER_UNRESOLVED",
                "severity": "INFO",
                "blocking": False,
                "status": "OPEN",
                "owner": None,
                "source_id": next(iter(qa["source_hashes"])),
                "description": q07["detail"],
                "resolution": None,
            })
        for check in checks:
            if check["status"] == "FAIL":
                exceptions.append(exception_from_check(
                    {**case, "gate_id": qa["gate_id"], "factory": qa["domain"]},
                    check,
                    True,
                ))
        return {
            "gate_id": qa["gate_id"],
            "qa_source": "EVIDENCE_DERIVED",
            "checks": checks,
            "source_hashes": qa["source_hashes"],
            "exceptions": exceptions,
        }

    checks = case["checks"]
    exceptions = [
        exception_from_check(case, check, check["status"] == "FAIL")
        for check in checks
        if check["status"] in {"REVIEW", "FAIL"}
    ]
    return {
        "gate_id": case["gate_id"],
        "qa_source": "CONTRACT_FIXTURE",
        "checks": checks,
        "source_hashes": {str(FIXTURE): file_hash(FIXTURE)},
        "exceptions": exceptions,
    }


def transition(case, normalized):
    qa_status = derive_status(normalized["checks"])
    active_blocking = any(
        row["blocking"] and row["status"] not in {"RESOLVED", "CLOSED"}
        for row in normalized["exceptions"]
    )
    if qa_status == "PASS" and not active_blocking:
        promotion_status, promotion_eligible = "READY", True
    elif qa_status == "REVIEW" and not active_blocking:
        promotion_status, promotion_eligible = "QUEUED", False
    else:
        promotion_status, promotion_eligible = "BLOCKED", False

    report = {
        "case_id": case["case_id"],
        "gate_id": normalized["gate_id"],
        "qa_source": normalized["qa_source"],
        "qa_status": qa_status,
        "promotion_status": promotion_status,
        "release_status": "HOLD",
        "promotion_eligible": promotion_eligible,
        "release_eligible": False,
        "exceptions": normalized["exceptions"],
        "source_hashes": normalized["source_hashes"],
    }
    for key, expected in case["expected"].items():
        assert report[key] == expected, (
            f"{case['case_id']}: {key} expected {expected!r}, got {report[key]!r}"
        )
    assert not active_blocking or report["promotion_eligible"] is False
    assert report["release_status"] == "HOLD" and report["release_eligible"] is False
    return report


def main():
    qa_module = load_qa_module()
    qa_cases = json.loads(QA_MATRIX.read_text())
    qa_reports = {case["gate_id"]: qa_module.make_report(case) for case in qa_cases}
    cases = json.loads(FIXTURE.read_text())
    reports = [transition(case, normalized_input(case, qa_reports)) for case in cases]

    assert [row["promotion_status"] for row in reports] == [
        "READY", "QUEUED", "BLOCKED", "BLOCKED"
    ]
    assert reports[0]["qa_source"] == "EVIDENCE_DERIVED"
    assert reports[3]["qa_source"] == "EVIDENCE_DERIVED"
    assert reports[3]["gate_id"].endswith("ANGELS-STUB-REGRESSION")
    assert reports[3]["promotion_eligible"] is False
    assert all(row["release_status"] != "RELEASED" for row in reports)

    first = canonical_hash(reports)
    second_reports = [
        transition(case, normalized_input(case, qa_reports)) for case in cases
    ]
    assert first == canonical_hash(second_reports), "deterministic report hash mismatch"

    output = {
        "schema_version": 1,
        "status": "PASS",
        "reports": reports,
        "report_sha256": first,
    }
    schema = json.loads(SCHEMA.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(output))
    assert not errors, "\n".join(error.message for error in errors)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
