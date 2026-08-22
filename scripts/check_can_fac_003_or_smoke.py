#!/usr/bin/env python3
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "evidence/candidate-factory-or-smoke/can-fac-003-portland.json"
EVIDENCE = ROOT / "evidence/candidate-factory-or-smoke/can-fac-003-source-evidence.json"


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def main() -> None:
    core = json.loads(CORE.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    if core.get("schema_version") != 2 or core.get("gate") != "CAN-FAC-003":
        fail("unexpected fixture contract")
    if core["jurisdiction"]["jurisdiction_id"] != "jurisdiction-or-portland":
        fail("unexpected Portland jurisdiction join")

    contests = {r["contest_id"]: r for r in core["contests"]}
    if len(contests) != 2:
        fail("expected two Portland council contests")
    election_id = core["election"]["election_id"]

    valid_offices = {
        "office-or-portland-councilor-district-3-7",
        "office-or-portland-councilor-district-3-8",
        "office-or-portland-councilor-district-3-9",
        "office-or-portland-councilor-district-4-10",
        "office-or-portland-councilor-district-4-11",
        "office-or-portland-councilor-district-4-12",
    }

    by_contest = defaultdict(list)
    seen_rel_ids = set()
    seen_offices = set()
    for rel in core["contest_offices"]:
        if rel["contest_office_id"] in seen_rel_ids:
            fail("duplicate contest_office_id")
        seen_rel_ids.add(rel["contest_office_id"])
        if rel["contest_id"] not in contests:
            fail(f"contest-office orphan: {rel['contest_office_id']}")
        if rel["office_id"] not in valid_offices:
            fail(f"unapproved OR office: {rel['office_id']}")
        if rel["office_id"] in seen_offices:
            fail(f"office reused across contests: {rel['office_id']}")
        seen_offices.add(rel["office_id"])
        if rel["relationship_status"] != "ACTIVE":
            fail(f"inactive contest-office relation: {rel['contest_office_id']}")
        by_contest[rel["contest_id"]].append(rel)

    for contest in contests.values():
        if contest["election_id"] != election_id:
            fail(f"contest orphaned from election: {contest['contest_id']}")
        if contest.get("office_id") is not None:
            fail(f"multi-winner contest must not select one arbitrary office: {contest['contest_id']}")
        if contest.get("office_resolution") != "CONTEST_OFFICE":
            fail(f"multi-winner contest missing relation resolution mode: {contest['contest_id']}")
        rels = by_contest[contest["contest_id"]]
        if len(rels) != contest["expected_seats"]:
            fail(f"contest office count != expected seats: {contest['contest_id']}")
        ordinals = sorted(r["seat_ordinal"] for r in rels)
        if ordinals != list(range(1, contest["expected_seats"] + 1)):
            fail(f"invalid seat ordinals: {contest['contest_id']}")

    persons = {r["person_id"]: r for r in core["persons"]}
    source_ids = set()
    hashes = set()
    for row in core["source_records"]:
        digest = hashlib.sha256(row["raw_payload_json"].encode("utf-8")).hexdigest()
        if digest != row["raw_row_sha256"]:
            fail(f"raw payload hash mismatch: {row['source_record_id']}")
        if row["source_record_id"] != f"sr-or-{digest}":
            fail(f"source record not content-addressed: {row['source_record_id']}")
        if digest in hashes:
            fail("duplicate raw payload hash")
        hashes.add(digest)
        source_ids.add(row["source_record_id"])

    candidacies = {r["candidacy_id"]: r for r in core["candidacies"]}
    if len(candidacies) != 4 or len(persons) != 4 or len(source_ids) != 4:
        fail("unexpected candidate entity counts")
    for row in candidacies.values():
        if row["person_id"] not in persons:
            fail(f"candidacy orphaned from person: {row['candidacy_id']}")
        if row["contest_id"] not in contests:
            fail(f"candidacy orphaned from contest: {row['candidacy_id']}")
        if row["primary_source_record_id"] not in source_ids:
            fail(f"candidacy orphaned from source: {row['candidacy_id']}")
        if row["candidacy_status"] != "Qualified":
            fail(f"unexpected status normalization: {row['candidacy_id']}")
        if row["party_affiliation_raw"]:
            fail(f"unsupported party inference: {row['candidacy_id']}")
        if row["incumbent_status"] != "Unknown":
            fail(f"unsupported incumbent inference: {row['candidacy_id']}")
        if "office_id" in row:
            fail(f"candidacy improperly assigned to an office slot: {row['candidacy_id']}")

    evidence_rows = {r["source_evidence_id"]: r for r in evidence["source_evidence"]}
    linked = set()
    for link in evidence["evidence_links"]:
        if link["source_evidence_id"] not in evidence_rows:
            fail(f"evidence link orphan: {link['evidence_link_id']}")
        if link["target_entity"] != "Candidacy" or link["target_id"] not in candidacies:
            fail(f"evidence target orphan: {link['evidence_link_id']}")
        linked.add(link["target_id"])
    if linked != set(candidacies):
        fail("not every candidacy has evidence")

    if not core["qa"].get("auditor_contest_excluded_until_office_governed"):
        fail("Auditor fail-closed boundary not preserved")

    print("CAN-FAC-003 PASS: 1 election, 2 multi-winner contests, 6 contest-office links, 4 qualified candidacies")


if __name__ == "__main__":
    main()
