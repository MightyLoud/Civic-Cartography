from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "apps-script" / "CensusApi.gs"
DOC = ROOT / "docs" / "census-api-apps-script.md"


def test_connector_files_exist() -> None:
    assert SCRIPT.is_file()
    assert DOC.is_file()


def test_security_and_fail_closed_contracts_are_explicit() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "CENSUS_API_KEY" in source
    assert "PropertiesService.getScriptProperties().getProperty" in source
    assert "cacheKey = 'census_api_v1_' + requestHash" in source
    assert "sourceUrlRedacted" in source
    assert "replace_staging cannot target a RAW- or SOURCE-labeled sheet" in source
    assert "sheet.getLastColumn() !== expectedHeaders.length" in source
    assert "['get', 'for', 'in', 'key']" in source
    assert "key: key" not in source
    assert "apiKey" not in source

    # A committed Census key would look like a long alphanumeric string literal.
    assert not re.findall(r"[\"']([A-Za-z0-9]{40})[\"']", source)


def test_documentation_keeps_the_key_out_of_cells_and_code() -> None:
    documentation = DOC.read_text(encoding="utf-8")

    assert "Script Property" in documentation
    assert "CENSUS_API_KEY" in documentation
    assert "Do not put the key in a sheet cell" in documentation
    assert "snapshot" in documentation
    assert "replace_staging" in documentation
    assert "RAW → normalized → QA → parity → tracker" in documentation


def test_apps_script_parses_and_pure_contracts_execute(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed; Apps Script syntax check skipped")

    javascript = tmp_path / "CensusApi.js"
    javascript.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    syntax = subprocess.run(
        [node, "--check", str(javascript)],
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

  var normalized = censusApiNormalizeRequest_({
    year: 2024,
    dataset: 'acs/acs5',
    get: ['NAME', 'B01003_001E'],
    for: 'state:*',
    in: ['region:3'],
    cacheSeconds: 0
  });
  assert(normalized.dataset === 'acs/acs5', 'dataset normalization failed');
  assert(normalized.redactedUrl.indexOf('get=NAME%2CB01003_001E') !== -1, 'selector encoding failed');
  assert(!/[?&]key=/.test(normalized.redactedUrl), 'redacted URL contains a key');

  var parsed = censusApiParseResponse_('[[' +
    '\"NAME\",\"B01003_001E\",\"state\"],[' +
    '\"Colorado\",\"6000000\",\"08\"]]');
  assert(parsed.length === 2 && parsed[1][2] === '08', 'response parsing failed');

  censusApiRequireStagingTarget_('STG_Census_CO_Counties');
  var blocked = false;
  try {
    censusApiRequireStagingTarget_('_RAW_Census_CO_Counties');
  } catch (error) {
    blocked = true;
  }
  assert(blocked, 'RAW overwrite guard did not fail closed');

  var redacted = censusApiRedactSecrets_('https://example.test?key=SECRET123&x=1', 'SECRET123');
  assert(redacted.indexOf('SECRET123') === -1, 'secret redaction failed');

  var reservedBlocked = false;
  try {
    censusApiNormalizeRequest_({
      year: 2024,
      dataset: 'acs/acs5',
      get: ['NAME'],
      predicates: { key: 'not-allowed' }
    });
  } catch (error) {
    reservedBlocked = true;
  }
  assert(reservedBlocked, 'reserved key predicate was not rejected');
`, context);
"""
    runtime = subprocess.run(
        [node, "-e", harness, str(javascript)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert runtime.returncode == 0, runtime.stderr
