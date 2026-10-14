#!/usr/bin/env python3
"""Regression tests for the read-only two-source dry-run runner."""
import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from monitor_dryrun import (
    CaptureFailure, SOURCES, CROSSWALK_SHA256, classify_name, identity_candidate,
    load_crosswalk, main, parse_cook, parse_cuyahoga, run_analysis, sha256,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class MonitorDryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crosswalk, cls.digests = load_crosswalk(FIXTURES / "approved_crosswalk.csv")
        cls.captures = {c: json.loads((FIXTURES / f"{c.lower()}_capture.json").read_text(encoding="utf-8")) for c in SOURCES}

    def test_sha256_standard_vectors(self):
        self.assertEqual(sha256(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(sha256("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_approved_crosswalk_exact(self):
        self.assertEqual(len(self.crosswalk), 40)
        self.assertEqual(self.digests["contract_sha256"], CROSSWALK_SHA256)
        for c in SOURCES:
            self.assertEqual(self.digests["archive_sha256"][c], SOURCES[c]["baseline_sha256"])

    def test_full_replay_fails_closed_with_four_review_cases(self):
        report = run_analysis(self.crosswalk, self.captures, self.digests)
        self.assertEqual(report["summary"]["observed_scoped_offices"], 40)
        self.assertEqual(report["summary"]["exact_display"], 36)
        self.assertEqual(report["summary"]["review_display"], 4)
        self.assertEqual(report["summary"]["name_conflicts"], 0)
        self.assertEqual(report["summary"]["workbook_writes"], 0)
        self.assertEqual(report["summary"]["monitor_cursor_writes"], 0)
        self.assertEqual(report["summary"]["live_HTTP_fetches"], 0)
        self.assertEqual(report["operating_status"], "HOLD — NO PRODUCTION SCAN")
        self.assertEqual({x["office_map_status"] for x in report["county_results"].values()}, {"PASS_SCOPE_STRUCTURE"})
        self.assertTrue(report["fail_closed_reasons"])
        self.assertEqual(len(report["county_results"]["Cook"]["out_of_scope_controls"]), 1)

    def test_cuyahoga_all_13_offices_deterministically_parsed(self):
        rows,excluded = parse_cuyahoga(self.captures["Cuyahoga"])
        self.assertEqual(len(rows), 13)
        self.assertEqual(len(set(x.seat_key for x in rows)), 13)
        self.assertEqual(len(excluded), 3)

    def test_cook_known_chief_judge_excluded(self):
        rows,excluded = parse_cook(self.captures["Cook"])
        self.assertEqual(len(rows), 27)
        self.assertEqual(len(set(x.seat_key for x in rows)), 27)
        self.assertIn("Chief Judge: known out-of-scope source entry", excluded)

    def test_wrong_source_endpoint_blocks(self):
        alt = copy.deepcopy(self.captures["Cook"])
        alt["source_url"] = "https://not-cook.example/all-people"
        with self.assertRaises(CaptureFailure): parse_cook(alt)

    def test_missing_official_row_holds_and_does_not_claim_complete(self):
        alt = copy.deepcopy(self.captures)
        alt["Cook"]["profiles"] = [p for p in alt["Cook"]["profiles"] if p["name"] != "Tara S. Stamps"]
        report = run_analysis(self.crosswalk, alt, self.digests)
        self.assertEqual(report["summary"]["observed_scoped_offices"], 39)
        self.assertIn("County Board · District 1", report["county_results"]["Cook"]["missing_seats"])
        self.assertEqual(report["county_results"]["Cook"]["office_map_status"], "BLOCKED_SCOPE_STRUCTURE")
        self.assertEqual(report["summary"]["workbook_writes"], 0)

    def test_same_office_twice_blocks(self):
        alt = copy.deepcopy(self.captures)
        duplicate = copy.deepcopy(alt["Cook"]["profiles"][0])
        duplicate["name_line"] = 289
        duplicate["role_line"] = 290
        alt["Cook"]["profiles"].append(duplicate)
        report = run_analysis(self.crosswalk, alt, self.digests)
        self.assertIn("County Board · District 16",report["county_results"]["Cook"]["duplicate_seats"])
        self.assertEqual(report["county_results"]["Cook"]["office_map_status"], "BLOCKED_SCOPE_STRUCTURE")

    def test_unrecognized_government_role_blocks(self):
        alt = copy.deepcopy(self.captures["Cook"])
        alt["profiles"][0]["role"] = "Unknown district office"
        with self.assertRaises(CaptureFailure):parse_cook(alt)

    def test_cuyahoga_duplicated_district_blocks(self):
        alt=copy.deepcopy(self.captures)
        for row in alt["Cuyahoga"]["line_refs"]:
            if row[0]==38:
                row[1] = "Patrick Kelly (District 2)"
        result = run_analysis(self.crosswalk, alt, self.digests)
        self.assertEqual(result["county_results"]["Cuyahoga"]["office_map_status"], "BLOCKED_SCOPE_STRUCTURE")
        self.assertIn("County Council · District 2",result["county_results"]["Cuyahoga"]["duplicate_seats"])

    def test_cuyahoga_missing_publishing_heading_blocks(self):
        alt=copy.deepcopy(self.captures["Cuyahoga"])
        alt["line_refs"] = [line for line in alt["line_refs"] if line[0]!=35]
        with self.assertRaises(CaptureFailure):parse_cuyahoga(alt)

    def test_new_holder_is_conflict_not_invented_change(self):
        alt = copy.deepcopy(self.captures)
        for p in alt["Cook"]["profiles"]:
            if p["role"] == "County Board Commissioner, 5th District":
                p["name"] = "Different Named Person"
        report=run_analysis(self.crosswalk,alt,self.digests)
        self.assertEqual(report["summary"]["name_conflicts"],1)
        changed=[o for o in report["observations"] if o["decision"]=="HOLD_NAME_CONFLICT"]
        self.assertEqual(len(changed),1)
        self.assertEqual(changed[0]["seat_key"],"County Board · District 5")
        self.assertFalse(changed[0]["canonical_change_authorized"])

    def test_punctuation_and_honorific_are_review_not_certified(self):
        self.assertEqual(identity_candidate("Frank J Aguilar"),identity_candidate("Frank J. Aguilar"))
        self.assertEqual(identity_candidate("Dr. Kisha McCaskill"),identity_candidate("Kisha McCaskill"))
        verdict,_ = classify_name("Dr. Kisha McCaskill","Kisha McCaskill","Kisha McCaskill",False)
        self.assertEqual(verdict,"REVIEW_FORMAT_VARIANT")
        verdict,_ = classify_name("Mark Casselberry","Mark Casselberry","Mark C. Casselberry",True)
        self.assertEqual(verdict,"REVIEW_EXISTING_IDENTITY")

    def test_mutated_approved_csv_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"changed.csv"
            src=(FIXTURES/"approved_crosswalk.csv").read_text(encoding="utf-8-sig")
            path.write_text(src.replace("Chris Ronayne","Different Person",1),encoding="utf-8")
            with self.assertRaises(CaptureFailure):load_crosswalk(path)

    def test_output_inside_fixture_directory_rejected(self):
        self.assertEqual(main(["--input-dir",str(FIXTURES),"--output-dir",str(FIXTURES/"bad")]),2)

    def test_only_local_files_written(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(main(["--input-dir",str(FIXTURES),"--output-dir",str(Path(temp)/"results")]),0)
            self.assertTrue((Path(temp)/"results"/"monitor_dryrun_report.json").is_file())
            self.assertTrue((Path(temp)/"results"/"monitor_dryrun_candidates.csv").is_file())
            report=json.loads((Path(temp)/"results"/"monitor_dryrun_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["operating_status"],"HOLD — NO PRODUCTION SCAN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
