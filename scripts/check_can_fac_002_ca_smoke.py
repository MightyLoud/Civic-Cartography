#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "evidence/candidate-factory-ca-smoke/can-fac-002-rohnert-park.json"
EVIDENCE = ROOT / "evidence/candidate-factory-ca-smoke/can-fac-002-source-evidence.json"


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def main() -> None:
    core = json.loads(CORE.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    source_records = core["source_records"]
    contests = {row["contest_id"]: row for row in core["contests"]}
    persons = {row["person_id"]: row for row in core["persons"]}
    candidacies = {row["candidacy_id"]: row for row in core["candidacies"]}
    evidence_rows = {row["source_evidence_id"]: row for row in evidence["source_evidence"]}

    if len(source_records) != 4 or len(contests) != 2 or len(persons) != 4 or len(candidacies) != 4:
        fail("unexpected entity counts")

    hashes = []
    source_ids = set()
    for row in source_records:
        digest = hashlib.sha256(row["raw_payload_json"].encode("utf-8")).hexdigest()
        if digest != row["raw_row_sha256"]:
            fail(f"raw payload hash mismatch: {row['source_record_id']}")
        if row["source_record_id"] != f"sr-ca-{digest}":
            fail(f"source_record_id is not content-addressed: {row['source_record_id']}")
        hashes.append(digest)
        source_ids.add(row["source_record_id"])
    if len(set(hashes)) != 4:
        fail("source hashes are not unique")

    valid_offices = {
        "office-ca-rohnert-park-district-2",
        "office-ca-rohnert-park-district-5",
    }
    election_id = core["election"]["election_id"]
    if core["election"]["administering_jurisdiction_id"] != "jurisdiction-ca-rohnert-park":
        fail("election does not resolve the governed CA jurisdiction")
    for contest in contests.values():
        if contest["election_id"] != election_id:
            fail(f"contest orphaned from election: {contest['contest_id']}")
        if contest["office_id"] not in valid_offices:
            fail(f"contest does not resolve an approved CA office: {contest['contest_id']}")

    for row in candidacies.values():
        if row["person_id"] not in persons:
            fail(f"candidacy orphaned from person: {row['candidacy_id']}")
        if row["contest_id"] not in contests:
            fail(f"candidacy orphaned from contest: {row['candidacy_id']}")
        if row["primary_source_record_id"] not in source_ids:
            fail(f"candidacy orphaned from source record: {row['candidacy_id']}")
        if row["candidacy_status"] != "Qualified":
            fail(f"unexpected normalized candidacy status: {row['candidacy_id']}")
        if row["party_affiliation_raw"]:
            fail(f"unsupported party inference: {row['candidacy_id']}")
        if row["incumbent_status"] != "Unknown":
            fail(f"unsupported incumbent inference: {row['candidacy_id']}")

    links = evidence["evidence_links"]
    if len(evidence_rows) != 4 or len(links) != 4:
        fail("unexpected evidence counts")
    linked_candidacies = set()
    for link in links:
        if link["source_evidence_id"] not in evidence_rows:
            fail(f"evidence link orphaned from evidence: {link['evidence_link_id']}")
        if link["target_entity"] != "Candidacy" or link["target_id"] not in candidacies:
            fail(f"evidence link orphaned from candidacy: {link['evidence_link_id']}")
        linked_candidacies.add(link["target_id"])
    if linked_candidacies != set(candidacies):
        fail("not every candidacy has evidence")

    print("CAN-FAC-002 PASS: 1 election, 2 contests, 4 candidacies, 4 source hashes, 4 evidence links")


if __name__ == "__main__":
    main()
