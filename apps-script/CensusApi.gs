/**
 * Secure U.S. Census Data API connector for Google Sheets.
 *
 * Credential contract:
 * - Store the API key only in the Script Property CENSUS_API_KEY.
 * - Never pass the key through a sheet cell, function argument, cache key,
 *   returned object, cell note, source URL, or execution log.
 *
 * Public functions:
 * - censusApiFetch(request)
 * - censusApiWriteToSheet(request, options)
 * - censusApiHealthCheck()
 * - censusApiInstallMenu()
 * - censusApiHealthCheckToUi()
 */

var CENSUS_API_CONFIG_ = Object.freeze({
  baseUrl: 'https://api.census.gov/data',
  keyProperty: 'CENSUS_API_KEY',
  defaultCacheSeconds: 3600,
  maxCacheSeconds: 21600,
  maxCachePayloadChars: 80000,
  defaultMaxAttempts: 4,
  defaultBaseDelayMs: 500,
  maxRequestedSelectors: 50,
  maxAttempts: 5,
  maxBaseDelayMs: 5000,
  writeChunkCells: 40000,
  executionLogSheet: 'ExecutionLog'
});

/**
 * Fetches a Census Data API response without writing to the workbook.
 *
 * @param {Object} request Request fields: year, dataset, get, for, in,
 *   predicates, cacheSeconds, maxAttempts, and baseDelayMs.
 * @return {Object} Parsed values and redacted provenance metadata.
 */
function censusApiFetch(request) {
  var normalized = censusApiNormalizeRequest_(request);
  var key = censusApiGetKey_();
  var requestHash = censusApiSha256Hex_(normalized.redactedUrl);
  var cacheKey = 'census_api_v1_' + requestHash;
  var cache = CacheService.getScriptCache();

  if (normalized.cacheSeconds > 0) {
    var cachedText = cache.get(cacheKey);
    if (cachedText) {
      var cached = JSON.parse(cachedText);
      cached.metadata.cacheHit = true;
      return cached;
    }
  }

  var authenticatedUrl = normalized.redactedUrl +
    (normalized.redactedUrl.indexOf('?') === -1 ? '?' : '&') +
    'key=' + encodeURIComponent(key);

  var responseText;
  try {
    responseText = censusApiFetchWithRetry_(authenticatedUrl, normalized, key);
  } catch (error) {
    throw new Error(censusApiRedactSecrets_(error && error.message ? error.message : String(error), key));
  }

  var values = censusApiParseResponse_(responseText);
  var result = {
    headers: values[0].slice(),
    rows: values.slice(1),
    values: values,
    metadata: {
      fetchedAtUtc: new Date().toISOString(),
      year: normalized.year,
      dataset: normalized.dataset,
      rowCount: Math.max(0, values.length - 1),
      columnCount: values[0].length,
      requestHash: requestHash,
      sourceUrlRedacted: normalized.redactedUrl,
      cacheHit: false
    }
  };

  if (normalized.cacheSeconds > 0) {
    var serialized = JSON.stringify(result);
    if (serialized.length <= CENSUS_API_CONFIG_.maxCachePayloadChars) {
      cache.put(cacheKey, serialized, normalized.cacheSeconds);
    }
  }

  return result;
}

/**
 * Fetches Census data and writes it using one explicit workbook mode.
 *
 * @param {Object} request See censusApiFetch().
 * @param {Object=} options mode, targetSheetName, sheetNamePrefix,
 *   writeExecutionLog.
 * @return {Object} Redacted metadata plus write disposition.
 */
function censusApiWriteToSheet(request, options) {
  options = options || {};
  var mode = String(options.mode || 'snapshot').toLowerCase();
  var allowedModes = ['snapshot', 'append', 'replace_staging'];
  if (allowedModes.indexOf(mode) === -1) {
    throw new Error('Unsupported write mode: ' + mode + '. Use snapshot, append, or replace_staging.');
  }

  var result = censusApiFetch(request);
  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error('No active spreadsheet is available. Run this function from a bound Apps Script project.');
  }

  var sheet;
  var valuesToWrite;
  var startRow;

  if (mode === 'snapshot') {
    var prefix = options.sheetNamePrefix || '_RAW_Census';
    var snapshotName = censusApiUniqueSheetName_(spreadsheet, prefix);
    sheet = spreadsheet.insertSheet(snapshotName);
    valuesToWrite = result.values;
    startRow = 1;
  } else {
    var targetSheetName = censusApiRequireSheetName_(options.targetSheetName);
    sheet = spreadsheet.getSheetByName(targetSheetName);
    if (!sheet) {
      throw new Error('Target sheet does not exist: ' + targetSheetName);
    }

    if (mode === 'append') {
      censusApiRequireMatchingHeaders_(sheet, result.headers);
      valuesToWrite = result.rows;
      startRow = Math.max(2, sheet.getLastRow() + 1);
    } else {
      censusApiRequireStagingTarget_(targetSheetName);
      var existingRange = sheet.getDataRange();
      existingRange.clearContent();
      existingRange.clearNote();
      valuesToWrite = result.values;
      startRow = 1;
    }
  }

  if (valuesToWrite.length > 0) {
    censusApiWriteTextValues_(sheet, startRow, 1, valuesToWrite);
  }

  if (mode !== 'append') {
    sheet.setFrozenRows(1);
    var note = JSON.stringify({
      fetchedAtUtc: result.metadata.fetchedAtUtc,
      year: result.metadata.year,
      dataset: result.metadata.dataset,
      rowCount: result.metadata.rowCount,
      columnCount: result.metadata.columnCount,
      requestHash: result.metadata.requestHash,
      sourceUrlRedacted: result.metadata.sourceUrlRedacted,
      cacheHit: result.metadata.cacheHit,
      writeMode: mode
    });
    sheet.getRange('A1').setNote(note);
  }

  var writeMetadata = {
    fetchedAtUtc: result.metadata.fetchedAtUtc,
    year: result.metadata.year,
    dataset: result.metadata.dataset,
    rowCount: result.metadata.rowCount,
    columnCount: result.metadata.columnCount,
    requestHash: result.metadata.requestHash,
    sourceUrlRedacted: result.metadata.sourceUrlRedacted,
    cacheHit: result.metadata.cacheHit,
    mode: mode,
    sheetName: sheet.getName(),
    startRow: startRow,
    rowsWritten: valuesToWrite.length
  };

  if (options.writeExecutionLog !== false) {
    censusApiAppendExecutionLog_(spreadsheet, writeMetadata);
  }

  return writeMetadata;
}

/**
 * Runs a small authenticated query without changing the workbook.
 *
 * @return {Object} Health-check status and redacted request metadata.
 */
function censusApiHealthCheck() {
  var result = censusApiFetch({
    year: 2024,
    dataset: 'acs/acs5',
    get: ['NAME', 'B01003_001E'],
    for: 'state:08',
    cacheSeconds: 0
  });

  if (result.rows.length !== 1) {
    throw new Error('Census API health check expected one Colorado row but received ' + result.rows.length + '.');
  }

  return {
    ok: true,
    dataset: result.metadata.dataset,
    year: result.metadata.year,
    rowCount: result.metadata.rowCount,
    name: result.rows[0][0],
    populationEstimate: result.rows[0][1],
    fetchedAtUtc: result.metadata.fetchedAtUtc,
    requestHash: result.metadata.requestHash
  };
}

/** Adds a Census API menu without defining a competing onOpen trigger. */
function censusApiInstallMenu() {
  SpreadsheetApp.getUi()
    .createMenu('Census API')
    .addItem('Run health check', 'censusApiHealthCheckToUi')
    .addToUi();
}

/** Menu-compatible health check. */
function censusApiHealthCheckToUi() {
  var ui = SpreadsheetApp.getUi();
  try {
    var status = censusApiHealthCheck();
    ui.alert(
      'Census API — PASS',
      status.name + '\nPopulation estimate: ' + status.populationEstimate +
        '\nFetched: ' + status.fetchedAtUtc +
        '\nRequest: ' + status.requestHash,
      ui.ButtonSet.OK
    );
  } catch (error) {
    ui.alert('Census API — FAIL', String(error && error.message ? error.message : error), ui.ButtonSet.OK);
    throw error;
  }
}

function censusApiNormalizeRequest_(request) {
  if (!request || Object.prototype.toString.call(request) !== '[object Object]') {
    throw new Error('Census API request must be an object.');
  }

  var year = Number(request.year);
  if (!isFinite(year) || Math.floor(year) !== year || year < 1990 || year > 2100) {
    throw new Error('Request year must be a four-digit integer from 1990 through 2100.');
  }

  var dataset = String(request.dataset || '').trim();
  if (!dataset || dataset.length > 160 || dataset.indexOf('..') !== -1 ||
      dataset.charAt(0) === '/' || dataset.charAt(dataset.length - 1) === '/' ||
      !/^[A-Za-z0-9._\/-]+$/.test(dataset)) {
    throw new Error('Dataset must be a safe relative Census dataset path, such as acs/acs5.');
  }

  var selectors = censusApiNormalizeSelectors_(request.get);
  var queryPairs = [['get', selectors.join(',')]];

  if (request.for !== undefined && request.for !== null && String(request.for).trim() !== '') {
    queryPairs.push(['for', censusApiNormalizeGeography_(request.for, 'for')]);
  }

  if (request.in !== undefined && request.in !== null && String(request.in).trim() !== '') {
    var inValue = Array.isArray(request.in) ? request.in.join(' ') : request.in;
    queryPairs.push(['in', censusApiNormalizeGeography_(inValue, 'in')]);
  }

  var predicates = request.predicates || {};
  if (Object.prototype.toString.call(predicates) !== '[object Object]') {
    throw new Error('predicates must be an object of additional Census query parameters.');
  }

  Object.keys(predicates).sort().forEach(function(key) {
    var normalizedKey = String(key).trim();
    if (!/^[A-Za-z0-9_.-]+$/.test(normalizedKey) ||
        ['get', 'for', 'in', 'key'].indexOf(normalizedKey.toLowerCase()) !== -1) {
      throw new Error('Unsafe or reserved predicate name: ' + normalizedKey);
    }
    var value = predicates[key];
    if (value === undefined || value === null) {
      throw new Error('Predicate ' + normalizedKey + ' cannot be null.');
    }
    var normalizedValue = Array.isArray(value) ? value.join(',') : String(value);
    if (normalizedValue.length > 1000 || /[\r\n]/.test(normalizedValue)) {
      throw new Error('Predicate ' + normalizedKey + ' is too long or contains a line break.');
    }
    queryPairs.push([normalizedKey, normalizedValue]);
  });

  var cacheSeconds = censusApiIntegerOption_(
    request.cacheSeconds,
    CENSUS_API_CONFIG_.defaultCacheSeconds,
    0,
    CENSUS_API_CONFIG_.maxCacheSeconds,
    'cacheSeconds'
  );
  var maxAttempts = censusApiIntegerOption_(
    request.maxAttempts,
    CENSUS_API_CONFIG_.defaultMaxAttempts,
    1,
    CENSUS_API_CONFIG_.maxAttempts,
    'maxAttempts'
  );
  var baseDelayMs = censusApiIntegerOption_(
    request.baseDelayMs,
    CENSUS_API_CONFIG_.defaultBaseDelayMs,
    100,
    CENSUS_API_CONFIG_.maxBaseDelayMs,
    'baseDelayMs'
  );

  var encodedQuery = queryPairs.map(function(pair) {
    return encodeURIComponent(pair[0]) + '=' + encodeURIComponent(pair[1]);
  }).join('&');

  return {
    year: year,
    dataset: dataset,
    cacheSeconds: cacheSeconds,
    maxAttempts: maxAttempts,
    baseDelayMs: baseDelayMs,
    redactedUrl: CENSUS_API_CONFIG_.baseUrl + '/' + year + '/' + dataset + '?' + encodedQuery
  };
}

function censusApiNormalizeSelectors_(getValue) {
  var selectors;
  if (Array.isArray(getValue)) {
    selectors = getValue.slice();
  } else if (typeof getValue === 'string') {
    selectors = getValue.split(',');
  } else {
    throw new Error('get must be an array or comma-separated string of Census variables/selectors.');
  }

  selectors = selectors.map(function(value) {
    return String(value).trim();
  }).filter(function(value) {
    return value !== '';
  });

  if (selectors.length === 0) {
    throw new Error('At least one Census variable/selector is required.');
  }
  if (selectors.length > CENSUS_API_CONFIG_.maxRequestedSelectors) {
    throw new Error('A request may contain at most ' + CENSUS_API_CONFIG_.maxRequestedSelectors + ' variables/selectors.');
  }

  var seen = {};
  selectors.forEach(function(selector) {
    if (selector.length > 120 || !/^[A-Za-z0-9_:.()\-*]+$/.test(selector)) {
      throw new Error('Unsafe Census variable/selector: ' + selector);
    }
    if (seen[selector]) {
      throw new Error('Duplicate Census variable/selector: ' + selector);
    }
    seen[selector] = true;
  });

  return selectors;
}

function censusApiNormalizeGeography_(value, fieldName) {
  var geography = String(value).trim().replace(/\s+/g, ' ');
  if (!geography || geography.length > 1000 || /[\r\n]/.test(geography) ||
      !/^[A-Za-z0-9_:.~*\- ,]+$/.test(geography)) {
    throw new Error('Unsafe Census geography predicate in ' + fieldName + '.');
  }
  return geography;
}

function censusApiIntegerOption_(value, defaultValue, minValue, maxValue, label) {
  if (value === undefined || value === null || value === '') {
    return defaultValue;
  }
  var numberValue = Number(value);
  if (!isFinite(numberValue) || Math.floor(numberValue) !== numberValue ||
      numberValue < minValue || numberValue > maxValue) {
    throw new Error(label + ' must be an integer from ' + minValue + ' through ' + maxValue + '.');
  }
  return numberValue;
}

function censusApiGetKey_() {
  var key = PropertiesService.getScriptProperties().getProperty(CENSUS_API_CONFIG_.keyProperty);
  key = key ? String(key).trim() : '';
  if (!key) {
    throw new Error(
      'Missing Script Property ' + CENSUS_API_CONFIG_.keyProperty +
      '. Add it in Apps Script Project Settings; never place the key in a sheet cell or source code.'
    );
  }
  if (key.length < 10 || /[\r\n\s]/.test(key)) {
    throw new Error('Script Property ' + CENSUS_API_CONFIG_.keyProperty + ' is malformed.');
  }
  return key;
}

function censusApiFetchWithRetry_(url, normalized, key) {
  var retryableCodes = {408: true, 429: true, 500: true, 502: true, 503: true, 504: true};
  var lastSummary = 'No response received.';

  for (var attempt = 1; attempt <= normalized.maxAttempts; attempt++) {
    var response;
    try {
      response = UrlFetchApp.fetch(url, {
        method: 'get',
        muteHttpExceptions: true,
        followRedirects: true,
        validateHttpsCertificates: true,
        headers: {'Accept': 'application/json'}
      });
    } catch (error) {
      lastSummary = censusApiRedactSecrets_(error && error.message ? error.message : String(error), key);
      if (attempt === normalized.maxAttempts) {
        break;
      }
      censusApiSleepBeforeRetry_(attempt, normalized.baseDelayMs, null);
      continue;
    }

    var statusCode = Number(response.getResponseCode());
    var responseText = response.getContentText('UTF-8');
    if (statusCode >= 200 && statusCode < 300) {
      return responseText;
    }

    lastSummary = 'HTTP ' + statusCode + ': ' + censusApiResponseExcerpt_(responseText, key);
    if (!retryableCodes[statusCode] || attempt === normalized.maxAttempts) {
      break;
    }

    censusApiSleepBeforeRetry_(attempt, normalized.baseDelayMs, response.getHeaders());
  }

  throw new Error('Census API request failed after ' + normalized.maxAttempts + ' attempt(s). ' + lastSummary);
}

function censusApiSleepBeforeRetry_(attempt, baseDelayMs, headers) {
  var retryAfterMs = 0;
  if (headers) {
    var retryAfter = headers['Retry-After'] || headers['retry-after'];
    if (retryAfter !== undefined && /^\d+$/.test(String(retryAfter))) {
      retryAfterMs = Number(retryAfter) * 1000;
    }
  }
  var exponentialMs = baseDelayMs * Math.pow(2, Math.max(0, attempt - 1));
  var jitterMs = Math.floor(Math.random() * Math.max(1, baseDelayMs));
  Utilities.sleep(Math.min(30000, Math.max(retryAfterMs, exponentialMs + jitterMs)));
}

function censusApiResponseExcerpt_(text, key) {
  var compact = String(text || '').replace(/\s+/g, ' ').trim();
  if (compact.length > 500) {
    compact = compact.substring(0, 500) + '…';
  }
  return censusApiRedactSecrets_(compact || '[empty response]', key);
}

function censusApiParseResponse_(responseText) {
  var parsed;
  try {
    parsed = JSON.parse(responseText);
  } catch (error) {
    throw new Error('Census API returned non-JSON content: ' + censusApiResponseExcerpt_(responseText, ''));
  }

  if (!Array.isArray(parsed) || parsed.length === 0 || !Array.isArray(parsed[0])) {
    var detail = parsed && parsed.error ? JSON.stringify(parsed.error) : JSON.stringify(parsed);
    throw new Error('Census API returned an unexpected payload: ' + censusApiResponseExcerpt_(detail, ''));
  }

  var width = parsed[0].length;
  if (width === 0) {
    throw new Error('Census API returned an empty header row.');
  }

  return parsed.map(function(row, index) {
    if (!Array.isArray(row) || row.length !== width) {
      throw new Error('Census API row ' + (index + 1) + ' does not match the header width.');
    }
    return row.map(function(value) {
      return value === null || value === undefined ? '' : String(value);
    });
  });
}

function censusApiRequireSheetName_(value) {
  var sheetName = String(value || '').trim();
  if (!sheetName) {
    throw new Error('targetSheetName is required for append and replace_staging modes.');
  }
  if (sheetName.length > 100 || /[\[\]:*?\/\\]/.test(sheetName)) {
    throw new Error('Invalid Google Sheets tab name: ' + sheetName);
  }
  return sheetName;
}

function censusApiRequireStagingTarget_(sheetName) {
  var tokens = String(sheetName).toUpperCase().split(/[^A-Z0-9]+/).filter(String);
  if (tokens.indexOf('RAW') !== -1 || tokens.indexOf('SOURCE') !== -1) {
    throw new Error('replace_staging cannot target a RAW- or SOURCE-labeled sheet: ' + sheetName);
  }
}

function censusApiRequireMatchingHeaders_(sheet, expectedHeaders) {
  if (sheet.getLastRow() < 1) {
    throw new Error('Append target has no header row: ' + sheet.getName());
  }
  if (sheet.getLastColumn() !== expectedHeaders.length) {
    throw new Error(
      'Append target header width is ' + sheet.getLastColumn() +
      ' but the Census response has ' + expectedHeaders.length + ' columns.'
    );
  }
  var observed = sheet.getRange(1, 1, 1, expectedHeaders.length).getDisplayValues()[0];
  for (var column = 0; column < expectedHeaders.length; column++) {
    if (String(observed[column]) !== String(expectedHeaders[column])) {
      throw new Error(
        'Append header mismatch at column ' + (column + 1) +
        ': expected "' + expectedHeaders[column] + '" but found "' + observed[column] + '".'
      );
    }
  }
}

function censusApiUniqueSheetName_(spreadsheet, prefix) {
  var cleanPrefix = String(prefix || '_RAW_Census')
    .replace(/[\[\]:*?\/\\]/g, '_')
    .replace(/\s+/g, '_')
    .replace(/_+/g, '_')
    .replace(/_+$/g, '');
  if (!cleanPrefix) {
    cleanPrefix = 'RAW_Census';
  }

  var timeZone = spreadsheet.getSpreadsheetTimeZone() || Session.getScriptTimeZone() || 'Etc/UTC';
  var timestamp = Utilities.formatDate(new Date(), timeZone, 'yyyyMMdd_HHmmss');
  var baseName = (cleanPrefix + '_' + timestamp).substring(0, 96);
  var candidate = baseName;
  var suffix = 2;
  while (spreadsheet.getSheetByName(candidate)) {
    candidate = (baseName.substring(0, 95 - String(suffix).length) + '_' + suffix).substring(0, 100);
    suffix++;
  }
  return candidate;
}

function censusApiWriteTextValues_(sheet, startRow, startColumn, values) {
  if (!values.length) {
    return;
  }
  var width = values[0].length;
  if (width === 0) {
    return;
  }

  values.forEach(function(row, index) {
    if (!Array.isArray(row) || row.length !== width) {
      throw new Error('Write row ' + (index + 1) + ' does not match the expected width.');
    }
  });

  censusApiEnsureGridSize_(sheet, startRow + values.length - 1, startColumn + width - 1);
  var chunkRows = Math.max(1, Math.floor(CENSUS_API_CONFIG_.writeChunkCells / width));

  for (var offset = 0; offset < values.length; offset += chunkRows) {
    var chunk = values.slice(offset, offset + chunkRows).map(function(row) {
      return row.map(censusApiSafeCellText_);
    });
    var range = sheet.getRange(startRow + offset, startColumn, chunk.length, width);
    range.setNumberFormat('@');
    range.setValues(chunk);
  }
}

function censusApiSafeCellText_(value) {
  var text = value === null || value === undefined ? '' : String(value);
  return text.charAt(0) === '=' ? "'" + text : text;
}

function censusApiEnsureGridSize_(sheet, requiredRows, requiredColumns) {
  var currentRows = sheet.getMaxRows();
  var currentColumns = sheet.getMaxColumns();
  if (requiredRows > currentRows) {
    sheet.insertRowsAfter(currentRows, requiredRows - currentRows);
  }
  if (requiredColumns > currentColumns) {
    sheet.insertColumnsAfter(currentColumns, requiredColumns - currentColumns);
  }
}

function censusApiAppendExecutionLog_(spreadsheet, metadata) {
  var logSheet = spreadsheet.getSheetByName(CENSUS_API_CONFIG_.executionLogSheet);
  if (!logSheet) {
    return;
  }
  var detail = [
    'dataset=' + metadata.year + '/' + metadata.dataset,
    'rows=' + metadata.rowCount,
    'columns=' + metadata.columnCount,
    'mode=' + metadata.mode,
    'sheet=' + metadata.sheetName,
    'request_hash=' + metadata.requestHash,
    'cache_hit=' + metadata.cacheHit
  ].join(' ');
  logSheet.appendRow([new Date(), 'INFO', 'CENSUS_API_FETCH', detail]);
}

function censusApiSha256Hex_(text) {
  var bytes = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    String(text),
    Utilities.Charset.UTF_8
  );
  return bytes.map(function(byte) {
    var normalized = byte < 0 ? byte + 256 : byte;
    return ('0' + normalized.toString(16)).slice(-2);
  }).join('');
}

function censusApiRedactSecrets_(text, key) {
  var redacted = String(text || '');
  if (key) {
    redacted = redacted.split(String(key)).join('[REDACTED]');
    redacted = redacted.split(encodeURIComponent(String(key))).join('[REDACTED]');
  }
  return redacted.replace(/([?&]key=)[^&\s]+/gi, '$1[REDACTED]');
}
