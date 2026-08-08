/**
 * First controlled immutable Census API snapshot for Nested Divisions.
 *
 * This file depends on apps-script/CensusApi.gs being installed in the same
 * bound Apps Script project and on CENSUS_API_KEY being present in Script
 * Properties.
 *
 * Snapshot contract:
 * - bound workbook: Nested Divisions (fail closed by spreadsheet ID)
 * - dataset: 2024 ACS 5-year detailed tables
 * - geography: every Colorado place
 * - variables: official name and total-population estimate
 * - identity columns returned by Census: state and place
 * - write mode: immutable timestamped RAW sheet
 * - cache: disabled so the snapshot records a live authenticated fetch
 * - QA: exact headers, row parity, Colorado-only scope, five-digit unique
 *   place IDs, nonblank names, nonnegative integer populations, no formulas
 */

var CENSUS_FIRST_SNAPSHOT_SPEC_ = Object.freeze({
  expectedSpreadsheetId: '139NETp-iofSoHtl_-IdSSph6xf_ePFVtR8l6KWYadSI',
  expectedSpreadsheetTitle: 'Nested Divisions',
  year: 2024,
  dataset: 'acs/acs5',
  selectors: Object.freeze(['NAME', 'B01003_001E']),
  geographyFor: 'place:*',
  geographyIn: 'state:08',
  expectedHeaders: Object.freeze(['NAME', 'B01003_001E', 'state', 'place']),
  sheetPrefix: '_RAW_Census_ACS5_2024_CO_Places_Population'
});

/**
 * Creates and verifies the first immutable Census RAW snapshot.
 *
 * @return {Object} Redacted fetch metadata and QA evidence.
 */
function censusApiCreateFirstControlledSnapshot() {
  var spreadsheet = censusApiRequireExpectedWorkbook_();

  if (typeof censusApiWriteToSheet !== 'function') {
    throw new Error(
      'CensusApi.gs is not installed in this Apps Script project. ' +
      'Install the merged connector before running the first snapshot.'
    );
  }

  var metadata = censusApiWriteToSheet(
    {
      year: CENSUS_FIRST_SNAPSHOT_SPEC_.year,
      dataset: CENSUS_FIRST_SNAPSHOT_SPEC_.dataset,
      get: CENSUS_FIRST_SNAPSHOT_SPEC_.selectors.slice(),
      for: CENSUS_FIRST_SNAPSHOT_SPEC_.geographyFor,
      in: CENSUS_FIRST_SNAPSHOT_SPEC_.geographyIn,
      cacheSeconds: 0,
      maxAttempts: 4,
      baseDelayMs: 500
    },
    {
      mode: 'snapshot',
      sheetNamePrefix: CENSUS_FIRST_SNAPSHOT_SPEC_.sheetPrefix,
      writeExecutionLog: true
    }
  );

  var qa = censusApiVerifyFirstControlledSnapshot_(spreadsheet, metadata);

  censusApiLogFirstSnapshotQa_(spreadsheet, metadata, qa);

  if (!qa.pass) {
    throw new Error(
      'The Census RAW snapshot was retained for evidence, but QA failed: ' +
      qa.failedChecks.join(', ') + '. Review sheet ' + metadata.sheetName + '.'
    );
  }

  return {
    ok: true,
    spreadsheetId: spreadsheet.getId(),
    spreadsheetTitle: spreadsheet.getName(),
    sheetName: metadata.sheetName,
    fetchedAtUtc: metadata.fetchedAtUtc,
    dataset: metadata.year + '/' + metadata.dataset,
    requestHash: metadata.requestHash,
    sourceUrlRedacted: metadata.sourceUrlRedacted,
    rowCount: qa.rowCount,
    columnCount: qa.columnCount,
    uniquePlaceCount: qa.uniquePlaceCount,
    contentSha256: qa.contentSha256,
    qaPass: true
  };
}

/** Menu/function-runner wrapper that displays the result in the spreadsheet. */
function censusApiCreateFirstControlledSnapshotToUi() {
  var ui = SpreadsheetApp.getUi();
  try {
    var result = censusApiCreateFirstControlledSnapshot();
    ui.alert(
      'Census RAW snapshot — PASS',
      'Workbook: ' + result.spreadsheetTitle + ' (' + result.spreadsheetId + ')' +
        '\nSheet: ' + result.sheetName +
        '\nRows: ' + result.rowCount +
        '\nUnique places: ' + result.uniquePlaceCount +
        '\nContent SHA-256: ' + result.contentSha256 +
        '\nFetched: ' + result.fetchedAtUtc,
      ui.ButtonSet.OK
    );
  } catch (error) {
    ui.alert(
      'Census RAW snapshot — REVIEW',
      String(error && error.message ? error.message : error),
      ui.ButtonSet.OK
    );
    throw error;
  }
}

/**
 * Reports the spreadsheet currently bound to this Apps Script project.
 *
 * @return {Object} Expected and observed workbook identity.
 */
function censusApiBindingCheck() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    return censusApiEvaluateBinding_('', '', '');
  }
  return censusApiEvaluateBinding_(
    spreadsheet.getId(),
    spreadsheet.getName(),
    spreadsheet.getUrl()
  );
}

/** Displays the binding result and fails when this is not Nested Divisions. */
function censusApiBindingCheckToUi() {
  var ui = SpreadsheetApp.getUi();
  var status = censusApiBindingCheck();
  var message = [
    'Expected: ' + status.expectedSpreadsheetTitle + ' (' + status.expectedSpreadsheetId + ')',
    'Observed: ' + (status.observedSpreadsheetTitle || '[none]') +
      ' (' + (status.observedSpreadsheetId || '[none]') + ')',
    'URL: ' + (status.observedSpreadsheetUrl || '[none]')
  ].join('\n');

  ui.alert(
    status.ok ? 'Census binding — PASS' : 'Census binding — FAIL',
    message,
    ui.ButtonSet.OK
  );

  if (!status.ok) {
    throw new Error(censusApiWrongWorkbookMessage_(status));
  }
  return status;
}

/**
 * Pure workbook-identity evaluator used by Apps Script and repository tests.
 *
 * @param {string} spreadsheetId Observed spreadsheet ID.
 * @param {string} spreadsheetTitle Observed spreadsheet title.
 * @param {string} spreadsheetUrl Observed spreadsheet URL.
 * @return {Object} Binding status.
 */
function censusApiEvaluateBinding_(spreadsheetId, spreadsheetTitle, spreadsheetUrl) {
  var observedId = String(spreadsheetId || '').trim();
  return {
    ok: observedId === CENSUS_FIRST_SNAPSHOT_SPEC_.expectedSpreadsheetId,
    expectedSpreadsheetId: CENSUS_FIRST_SNAPSHOT_SPEC_.expectedSpreadsheetId,
    expectedSpreadsheetTitle: CENSUS_FIRST_SNAPSHOT_SPEC_.expectedSpreadsheetTitle,
    observedSpreadsheetId: observedId,
    observedSpreadsheetTitle: String(spreadsheetTitle || '').trim(),
    observedSpreadsheetUrl: String(spreadsheetUrl || '').trim()
  };
}

function censusApiRequireExpectedWorkbook_() {
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var status = spreadsheet
    ? censusApiEvaluateBinding_(
        spreadsheet.getId(),
        spreadsheet.getName(),
        spreadsheet.getUrl()
      )
    : censusApiEvaluateBinding_('', '', '');

  if (!status.ok) {
    throw new Error(censusApiWrongWorkbookMessage_(status));
  }
  return spreadsheet;
}

function censusApiWrongWorkbookMessage_(status) {
  return [
    'Wrong bound spreadsheet. No Census request or sheet write was attempted.',
    'Expected ' + status.expectedSpreadsheetTitle +
      ' (' + status.expectedSpreadsheetId + ').',
    'Observed ' + (status.observedSpreadsheetTitle || '[none]') +
      ' (' + (status.observedSpreadsheetId || '[none]') + ').',
    'Open the exact Nested Divisions workbook and use Extensions → Apps Script.'
  ].join(' ');
}

function censusApiVerifyFirstControlledSnapshot_(spreadsheet, metadata) {
  if (!spreadsheet) {
    throw new Error('No active spreadsheet is available for snapshot verification.');
  }
  if (!metadata || !metadata.sheetName) {
    throw new Error('Snapshot metadata is missing the created sheet name.');
  }

  var sheet = spreadsheet.getSheetByName(metadata.sheetName);
  if (!sheet) {
    throw new Error('Created snapshot sheet cannot be found: ' + metadata.sheetName);
  }

  var lastRow = sheet.getLastRow();
  var lastColumn = sheet.getLastColumn();
  var values = lastRow > 0 && lastColumn > 0
    ? sheet.getRange(1, 1, lastRow, lastColumn).getDisplayValues()
    : [];
  var formulas = lastRow > 0 && lastColumn > 0
    ? sheet.getRange(1, 1, lastRow, lastColumn).getFormulas()
    : [];

  var qa = censusApiEvaluateFirstSnapshotValues_(values, metadata);
  qa.formulaCellCount = censusApiCountNonblankCells_(formulas);
  qa.checks.noFormulas = qa.formulaCellCount === 0;
  qa.columnCount = lastColumn;
  qa.sheetLastRow = lastRow;
  qa.sheetLastColumn = lastColumn;
  qa.contentSha256 = typeof censusApiSha256Hex_ === 'function'
    ? censusApiSha256Hex_(JSON.stringify(values))
    : '';

  qa.failedChecks = Object.keys(qa.checks).filter(function(checkName) {
    return qa.checks[checkName] !== true;
  });
  qa.pass = qa.failedChecks.length === 0;
  return qa;
}

/**
 * Pure QA evaluator used by Apps Script and repository tests.
 *
 * @param {Array<Array<string>>} values Complete sheet values including header.
 * @param {Object} metadata Redacted fetch/write metadata.
 * @return {Object} QA counts and check outcomes.
 */
function censusApiEvaluateFirstSnapshotValues_(values, metadata) {
  values = Array.isArray(values) ? values : [];
  metadata = metadata || {};

  var expectedHeaders = CENSUS_FIRST_SNAPSHOT_SPEC_.expectedHeaders.slice();
  var observedHeaders = values.length > 0 && Array.isArray(values[0])
    ? values[0].map(String)
    : [];
  var rows = values.slice(1);
  var duplicatePlaceCount = 0;
  var invalidStateCount = 0;
  var invalidPlaceCount = 0;
  var blankNameCount = 0;
  var invalidPopulationCount = 0;
  var malformedWidthCount = 0;
  var seenPlaces = {};

  rows.forEach(function(row) {
    if (!Array.isArray(row) || row.length !== expectedHeaders.length) {
      malformedWidthCount++;
      return;
    }

    var name = String(row[0] || '').trim();
    var population = String(row[1] || '').trim();
    var state = String(row[2] || '').trim();
    var place = String(row[3] || '').trim();

    if (!name) {
      blankNameCount++;
    }
    if (!/^\d+$/.test(population) || Number(population) < 0) {
      invalidPopulationCount++;
    }
    if (state !== '08') {
      invalidStateCount++;
    }
    if (!/^\d{5}$/.test(place)) {
      invalidPlaceCount++;
    } else if (seenPlaces[place]) {
      duplicatePlaceCount++;
    } else {
      seenPlaces[place] = true;
    }
  });

  var expectedApiRows = Number(metadata.rowCount);
  var expectedWrittenRows = Number(metadata.rowsWritten);
  var rowCount = rows.length;
  var headerMatch = expectedHeaders.length === observedHeaders.length &&
    expectedHeaders.every(function(header, index) {
      return observedHeaders[index] === header;
    });

  return {
    rowCount: rowCount,
    columnCount: observedHeaders.length,
    uniquePlaceCount: Object.keys(seenPlaces).length,
    duplicatePlaceCount: duplicatePlaceCount,
    invalidStateCount: invalidStateCount,
    invalidPlaceCount: invalidPlaceCount,
    blankNameCount: blankNameCount,
    invalidPopulationCount: invalidPopulationCount,
    malformedWidthCount: malformedWidthCount,
    checks: {
      nonemptySnapshot: rowCount > 0,
      exactHeaders: headerMatch,
      metadataRowParity: isFinite(expectedApiRows) && expectedApiRows === rowCount,
      writeRowParity: isFinite(expectedWrittenRows) && expectedWrittenRows === rowCount + 1,
      exactColumnCount: observedHeaders.length === expectedHeaders.length,
      uniformRowWidth: malformedWidthCount === 0,
      coloradoOnly: invalidStateCount === 0,
      validPlaceIds: invalidPlaceCount === 0,
      uniquePlaceIds: duplicatePlaceCount === 0 && Object.keys(seenPlaces).length === rowCount,
      nonblankNames: blankNameCount === 0,
      validPopulationEstimates: invalidPopulationCount === 0
    },
    failedChecks: [],
    pass: false
  };
}

function censusApiCountNonblankCells_(matrix) {
  var count = 0;
  (Array.isArray(matrix) ? matrix : []).forEach(function(row) {
    (Array.isArray(row) ? row : []).forEach(function(value) {
      if (String(value || '') !== '') {
        count++;
      }
    });
  });
  return count;
}

function censusApiLogFirstSnapshotQa_(spreadsheet, metadata, qa) {
  var logSheet = spreadsheet.getSheetByName('ExecutionLog');
  if (!logSheet) {
    return;
  }

  var detail = [
    'sheet=' + metadata.sheetName,
    'dataset=' + metadata.year + '/' + metadata.dataset,
    'rows=' + qa.rowCount,
    'unique_places=' + qa.uniquePlaceCount,
    'duplicate_places=' + qa.duplicatePlaceCount,
    'invalid_states=' + qa.invalidStateCount,
    'invalid_place_ids=' + qa.invalidPlaceCount,
    'blank_names=' + qa.blankNameCount,
    'invalid_population=' + qa.invalidPopulationCount,
    'formula_cells=' + qa.formulaCellCount,
    'content_sha256=' + qa.contentSha256,
    'qa=' + (qa.pass ? 'PASS' : 'FAIL'),
    'failed_checks=' + (qa.failedChecks.length ? qa.failedChecks.join('|') : 'none')
  ].join(' ');

  logSheet.appendRow([
    new Date(),
    qa.pass ? 'INFO' : 'ERROR',
    'CENSUS_API_SNAPSHOT_QA',
    detail
  ]);
}
