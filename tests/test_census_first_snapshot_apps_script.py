from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONNECTOR = ROOT / "apps-script" / "CensusApi.gs"
SNAPSHOT = ROOT / "apps-script" / "CensusFirstSnapshot.gs"
DOC = ROOT / "docs" / "census-first-controlled-snapshot.md"


def test_snapshot_artifacts_exist() -> None:
    assert CONNECTOR.is_file()
    assert SNAPSHOT.is_file()
    assert DOC.is_file()


def test_snapshot_contract_is_immutable_and_key_free() -> None:
    source = SNAPSHOT.read_text(encoding="utf-8")

    assert "year: 2024" in source
    assert "dataset: 'acs/acs5'" in source
    assert "['NAME', 'B01003_001E']" in source
    assert "geographyFor: 'place:*'" in source
    assert "geographyIn: 'state:08'" in source
    assert "['NAME', 'B01003_001E', 'state', 'place']" in source
    assert "mode: 'snapshot'" in source
    assert "cacheSeconds: 0" in source
    assert "CENSUS_API_SNAPSHOT_QA" in source
    assert "CENSUS_API_KEY" in source
    assert "key=" not in source


def test_documentation_preserves_authority_and_completion_boundaries() -> None:
    documentation = DOC.read_text(encoding="utf-8")

    assert "does not replace the current TIGER/Line source authority" in documentation
    assert "RAW snapshot exists" in documentation
    assert "snapshot QA passes" in documentation
    assert "downstream QA and parity pass" in documentation
    assert "tracker records completion" in documentation
    assert "Creating the RAW sheet alone does not complete" in documentation


def test_snapshot_javascript_parses_and_pure_qa_contract_executes(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed; Apps Script syntax check skipped")

    combined = tmp_path / "CensusCombined.js"
    combined.write_text(
        CONNECTOR.read_text(encoding="utf-8")
        + "\n"
        + SNAPSHOT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    syntax = subprocess.run(
        [node, "--check", str(combined)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert syntax.returncode == 0, syntax.stderr

    harness = r"""
const fs = require('fs');
const vm = require('vm');
const context = { console };
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
vm.runInContext(`
  function assert(condition, message) {
    if (!condition) throw new Error(message);
  }

  var valid = censusApiEvaluateFirstSnapshotValues_([
    ['NAME', 'B01003_001E', 'state', 'place'],
    ['Colorado Springs city, Colorado', '491530', '08', '16000'],
    ['Denver city, Colorado', '713252', '08', '20000']
  ], {rowCount: 2, rowsWritten: 3});

  assert(valid.checks.nonemptySnapshot, 'snapshot should be nonempty');
  assert(valid.checks.exactHeaders, 'headers should match');
  assert(valid.checks.metadataRowParity, 'API row parity should pass');
  assert(valid.checks.writeRowParity, 'write row parity should pass');
  assert(valid.checks.coloradoOnly, 'Colorado scope should pass');
  assert(valid.checks.validPlaceIds, 'place ID format should pass');
  assert(valid.checks.uniquePlaceIds, 'place IDs should be unique');
  assert(valid.checks.nonblankNames, 'names should be present');
  assert(valid.checks.validPopulationEstimates, 'population values should pass');
  assert(valid.uniquePlaceCount === 2, 'unique place count should be two');

  var invalid = censusApiEvaluateFirstSnapshotValues_([
    ['NAME', 'B01003_001E', 'state', 'place'],
    ['', '-1', '09', '20000'],
    ['Duplicate', '100', '08', '20000']
  ], {rowCount: 2, rowsWritten: 3});

  assert(!invalid.checks.coloradoOnly, 'wrong state must fail');
  assert(!invalid.checks.uniquePlaceIds, 'duplicate place must fail');
  assert(!invalid.checks.nonblankNames, 'blank name must fail');
  assert(!invalid.checks.validPopulationEstimates, 'negative population must fail');
`, context);
"""

    runtime = subprocess.run(
        [node, "-e", harness, str(combined)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert runtime.returncode == 0, runtime.stderr
