#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

FIXTURE = Path("tests/fixtures/orch_fac_002_orchestration.json")
FIXTURE_SCHEMA = Path("schemas/orch-fac-002-orchestration.schema.json")
REPORT_SCHEMA = Path("schemas/orch-fac-002-report.schema.json")
ORCH1 = Path("scripts/validate_orch_fac_001.py")
STAGES = ("source", "domain", "qa", "rel")


def load_orch1():
    spec = importlib.util.spec_from_file_location("orch_fac_001", ORCH1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_hash(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(schema_path, payload):
    schema = json.loads(schema_path.read_text())
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    assert not errors, "\n".join(error.message for error in errors)


def actor_for(stage, case):
    return {
        "source": "SRC-FAC",
        "domain": case["domain_factory"],
        "qa": "QA-FAC",
        "rel": "REL-FAC",
    }[stage]


def assert_events(case_id, events):
    held = None
    routed = False
    for event in events:
        kind = event["event"]
        if routed:
            raise AssertionError(f"{case_id}: event emitted after terminal route")
        if kind == "acquire":
            assert held is None, f"{case_id}: simultaneous writers"
            held = event["actor"]
        elif kind == "stage_result":
            assert held == event["actor"], f"{case_id}: result without owner"
        elif kind == "release":
            assert held == event["actor"], f"{case_id}: release without owner"
            held = None
        elif kind == "reject":
            assert held is None, f"{case_id}: rejection while lock held"
        elif kind == "route":
            assert held is None, f"{case_id}: route while lock held"
            routed = True
    assert held is None and routed, f"{case_id}: nonterminal event stream"


def run_case(case, nonwriting, orch1):
    registry = []
    events = []
    stages_executed = 0
    terminal_status = None
    promotion_status = None
    terminal_route = None

    for stage in STAGES:
        actor = actor_for(stage, case)
        if actor in nonwriting:
            assert orch1.assert_registry(case["case_id"], registry) == 0
            events.append({"event": "reject", "stage": stage, "actor": actor, "reason": "READ_ONLY"})
            terminal_status, promotion_status, terminal_route = "REVIEW", "QUEUED", "EXCEPTION-QUEUE"
            events.append({"event": "route", "status": terminal_status, "target": terminal_route})
            break

        checks = case["stage_checks"].get(stage)
        assert checks is not None, f"{case['case_id']}: activated stage {stage} lacks checks"

        row = {
            "conversation_id": actor,
            "task_id": f"{case['case_id']}:{stage}",
            "write_surface": [f"fixture:{case['case_id']}:{stage}"],
            "status": "ACTIVE — LOCK HELD",
            "lock_state": "HELD",
            "lock_owner": actor,
            "handoff_to": "",
        }
        registry.append(row)
        assert orch1.assert_registry(case["case_id"], registry) == 1
        events.append({"event": "acquire", "stage": stage, "actor": actor})
        stages_executed += 1

        status = orch1.qa_status(checks)
        events.append({"event": "stage_result", "stage": stage, "actor": actor, "status": status})

        row["lock_state"] = "RELEASED"
        row["lock_owner"] = "NONE"
        row["status"] = f"{stage.upper()} — {status} — LOCK RELEASED"
        assert orch1.assert_registry(case["case_id"], registry) == 0
        events.append({"event": "release", "stage": stage, "actor": actor, "status": status})

        if status == "PASS" and stage != "rel":
            continue

        promotion_status, _, _, _, default_route = orch1.rel_transition(status)
        terminal_status = status
        if stage == "rel" and status == "PASS":
            terminal_route = case.get("final_handoff")
            assert terminal_route == "PROGRAM-CONTROL"
        else:
            terminal_route = default_route
        events.append({"event": "route", "status": terminal_status, "target": terminal_route})
        break

    assert terminal_status is not None
    assert_events(case["case_id"], events)
    return {
        "case_id": case["case_id"],
        "terminal_status": terminal_status,
        "promotion_status": promotion_status,
        "release_status": "HOLD",
        "terminal_route": terminal_route,
        "stages_executed": stages_executed,
        "held_locks": orch1.assert_registry(case["case_id"], registry),
        "events": events,
    }


def main():
    data = json.loads(FIXTURE.read_text())
    validate(FIXTURE_SCHEMA, data)
    orch1 = load_orch1()
    nonwriting = set(data["nonwriting_workers"])

    first = [run_case(case, nonwriting, orch1) for case in data["cases"]]
    second = [run_case(case, nonwriting, orch1) for case in data["cases"]]
    digest = canonical_hash(first)
    assert digest == canonical_hash(second), "orchestration report is not deterministic"

    coverage = set()
    for case, result in zip(data["cases"], first):
        if case["case_id"] == "happy-path-promotion-handoff":
            assert result["terminal_status"] == "PASS"
            assert result["promotion_status"] == "READY"
            assert result["release_status"] == "HOLD"
            assert result["stages_executed"] == 4
        elif case["case_id"] == "read-only-monitor-rejected":
            assert result["terminal_status"] == "REVIEW"
            assert result["stages_executed"] == 1
            assert result["terminal_route"] == "EXCEPTION-QUEUE"
        else:
            terminal = next(
                event for event in result["events"] if event["event"] == "stage_result"
                and event["status"] != "PASS"
            )
            coverage.add((terminal["stage"], terminal["status"]))
            assert result["terminal_route"] == (
                "EXCEPTION-QUEUE" if terminal["status"] == "REVIEW" else "REMEDIATION"
            )
        assert result["held_locks"] == 0

    assert coverage == {
        (stage, status) for stage in STAGES for status in ("REVIEW", "FAIL")
    }

    output = {
        "schema_version": 1,
        "gate_id": "ORCH-FAC-002",
        "status": "PASS",
        "deterministic": True,
        "fixture_sha256": file_hash(FIXTURE),
        "results": first,
        "report_sha256": digest,
    }
    validate(REPORT_SCHEMA, output)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
