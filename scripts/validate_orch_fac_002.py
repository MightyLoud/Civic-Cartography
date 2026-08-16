#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

FIXTURE = Path("tests/fixtures/orch_fac_002_orchestration.json")
STAGE_ORDER = ("source", "domain", "qa", "release")
VALID_OUTCOMES = {"PASS", "REVIEW", "FAIL"}


def canonical_hash(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def actor_for(stage, case):
    return {
        "source": "SRC-FAC",
        "domain": case["domain_factory"],
        "qa": "QA-FAC",
        "release": "REL-FAC",
    }[stage]


def validate_fixture(data):
    if data.get("version") != 1:
        raise AssertionError("fixture version must be 1")
    if not isinstance(data.get("read_only_workers"), list):
        raise AssertionError("read_only_workers must be a list")
    if len(data["read_only_workers"]) != len(set(data["read_only_workers"])):
        raise AssertionError("read_only_workers must be unique")
    if not data.get("cases"):
        raise AssertionError("at least one case is required")

    seen = set()
    for case in data["cases"]:
        cid = case.get("case_id")
        if not cid or cid in seen:
            raise AssertionError("case_id must be non-empty and unique")
        seen.add(cid)
        if not case.get("domain_factory") or not case.get("final_handoff"):
            raise AssertionError(f"{cid}: domain_factory and final_handoff are required")
        outcomes = case.get("outcomes", {})
        if set(outcomes) != set(STAGE_ORDER):
            raise AssertionError(f"{cid}: outcomes must define exactly {STAGE_ORDER}")
        if any(value not in VALID_OUTCOMES for value in outcomes.values()):
            raise AssertionError(f"{cid}: invalid outcome")


def assert_event_invariants(case_id, events):
    held = None
    prior_kind = None
    for event in events:
        kind = event["event"]
        actor = event.get("actor")
        if kind == "acquire":
            if held is not None:
                raise AssertionError(f"{case_id}: multiple simultaneous writers")
            if prior_kind == "acquire":
                raise AssertionError(f"{case_id}: downstream activation before release")
            held = actor
        elif kind == "release":
            if held != actor:
                raise AssertionError(f"{case_id}: release without matching held lock")
            held = None
        elif kind in {"route", "reject"}:
            if held is not None:
                raise AssertionError(f"{case_id}: terminal routing while lock still held")
        else:
            raise AssertionError(f"{case_id}: unknown event {kind}")
        prior_kind = kind

    if held is not None:
        raise AssertionError(f"{case_id}: held lock leaked at terminal state")


def run_case(case, read_only_workers):
    events = []
    held_actor = None
    stages_executed = 0
    terminal_status = None
    terminal_route = None

    for stage in STAGE_ORDER:
        actor = actor_for(stage, case)

        if actor in read_only_workers:
            if held_actor is not None:
                raise AssertionError(f"{case['case_id']}: read-only rejection with lock held")
            events.append({"event": "reject", "stage": stage, "actor": actor, "reason": "READ_ONLY"})
            terminal_status = "REVIEW"
            terminal_route = "EXCEPTION-QUEUE"
            events.append({"event": "route", "status": terminal_status, "target": terminal_route})
            break

        if held_actor is not None:
            raise AssertionError(f"{case['case_id']}: attempted acquire before prior release")

        held_actor = actor
        events.append({"event": "acquire", "stage": stage, "actor": actor})
        stages_executed += 1

        outcome = case["outcomes"][stage]

        # The current writer always releases before any handoff, successor activation,
        # exception routing, or remediation routing.
        events.append({"event": "release", "stage": stage, "actor": actor, "outcome": outcome})
        held_actor = None

        if outcome == "PASS":
            if stage == "release":
                terminal_status = "PASS"
                terminal_route = case["final_handoff"]
                events.append({"event": "route", "status": terminal_status, "target": terminal_route})
                break
            continue

        if outcome == "REVIEW":
            terminal_status = "REVIEW"
            terminal_route = "EXCEPTION-QUEUE"
            events.append({"event": "route", "status": terminal_status, "target": terminal_route})
            break

        terminal_status = "FAIL"
        terminal_route = "REMEDIATION"
        events.append({"event": "route", "status": terminal_status, "target": terminal_route})
        break

    if terminal_status is None or terminal_route is None:
        raise AssertionError(f"{case['case_id']}: no terminal route")

    assert_event_invariants(case["case_id"], events)

    # A non-PASS terminal may not activate a successor after the terminal route.
    route_index = next(i for i, event in enumerate(events) if event["event"] == "route")
    if any(event["event"] == "acquire" for event in events[route_index + 1:]):
        raise AssertionError(f"{case['case_id']}: successor writer activated after terminal route")

    result = {
        "case_id": case["case_id"],
        "terminal_status": terminal_status,
        "terminal_route": terminal_route,
        "stages_executed": stages_executed,
        "held_locks": 0 if held_actor is None else 1,
        "events": events,
    }

    for key, expected in case["expected"].items():
        if result[key] != expected:
            raise AssertionError(
                f"{case['case_id']} {key}: got {result[key]!r}, expected {expected!r}"
            )

    return result


def main():
    data = json.loads(FIXTURE.read_text())
    validate_fixture(data)
    read_only_workers = set(data["read_only_workers"])

    first = [run_case(case, read_only_workers) for case in data["cases"]]
    second = [run_case(case, read_only_workers) for case in data["cases"]]
    h1 = canonical_hash(first)
    h2 = canonical_hash(second)
    if h1 != h2:
        raise AssertionError("orchestration output is not deterministic")

    print(json.dumps({
        "gate_id": "ORCH-FAC-002",
        "status": "PASS",
        "cases": len(first),
        "deterministic": True,
        "report_sha256": h1,
        "results": [
            {k: result[k] for k in (
                "case_id", "terminal_status", "terminal_route", "stages_executed", "held_locks"
            )}
            for result in first
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
