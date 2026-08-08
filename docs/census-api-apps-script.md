# Census Data API connector for Google Sheets

## Purpose

`apps-script/CensusApi.gs` is the secure workbook-side connector for Census Data API requests. It is designed for the existing civic-data pipeline:

```text
Census API request
→ immutable RAW snapshot or controlled staging write
→ existing normalization
→ QA and parity
→ tracker completion
```

The command-center workbook should store only the governed connector reference and status. Install the script in the Apps Script project bound to the authoritative data workbook that owns the RAW and normalized geography layers.

## Security contract

- The key is stored only in the Apps Script **Script Property** named `CENSUS_API_KEY`.
- The key is loaded only when a request is sent.
- The key is excluded from cache keys, return objects, cell notes, sheet data, and `ExecutionLog` rows.
- Errors and URLs are redacted before they are surfaced.
- The repository contains no API key or placeholder that could be mistaken for a key.

## One-time installation

1. Request and activate a free Census API key.
2. Open the authoritative workbook.
3. Select **Extensions → Apps Script**.
4. Add a script file named `CensusApi` and copy in `apps-script/CensusApi.gs`.
5. Open **Project Settings → Script Properties**.
6. Add:

   | Property | Value |
   |---|---|
   | `CENSUS_API_KEY` | your activated key |

7. Run `censusApiHealthCheck` once and authorize the script.
8. Confirm the returned object contains `ok: true`.

Do not put the key in a sheet cell, named range, formula, source URL, code comment, GitHub secret committed to the repository, or execution log.

## Public functions

### `censusApiFetch(request)`

Returns Census data without writing to a sheet:

```javascript
var result = censusApiFetch({
  year: 2024,
  dataset: 'acs/acs5',
  get: ['NAME', 'B01003_001E'],
  for: 'state:*'
});

// result.headers
// result.rows
// result.values   // header row + data rows
// result.metadata // redacted provenance and request hash
```

Supported request fields:

| Field | Required | Meaning |
|---|---:|---|
| `year` | Yes | Census dataset vintage |
| `dataset` | Yes | Relative dataset path, such as `acs/acs5` |
| `get` | Yes | Array or comma-separated variables |
| `for` | No | Census geography predicate |
| `in` | No | Parent geography predicate; arrays are joined with spaces |
| `predicates` | No | Additional dataset predicates |
| `cacheSeconds` | No | `0` disables cache; default `3600`; maximum `21600` |
| `maxAttempts` | No | Retry attempts from `1` to `5`; default `4` |
| `baseDelayMs` | No | Initial retry delay from `100` to `5000` ms |

### `censusApiWriteToSheet(request, options)`

Fetches data and applies one explicit write mode:

| Mode | Behavior | Guardrail |
|---|---|---|
| `snapshot` | Creates a new timestamped sheet | Default; never overwrites an existing tab |
| `append` | Appends rows to an existing table | Blocks unless headers match exactly |
| `replace_staging` | Replaces a staging/output tab | Blocks RAW- or source-labeled tab names |

The writer formats all values as text to preserve identifiers and leading zeroes. It also protects values beginning with `=` from being interpreted as formulas.

Immutable RAW example:

```javascript
var metadata = censusApiWriteToSheet(
  {
    year: 2024,
    dataset: 'acs/acs5',
    get: ['NAME', 'B01003_001E'],
    for: 'place:*',
    in: 'state:08'
  },
  {
    mode: 'snapshot',
    sheetNamePrefix: '_RAW_Census_ACS5_CO_Places'
  }
);
```

Controlled staging example:

```javascript
censusApiWriteToSheet(
  {
    year: 2024,
    dataset: 'acs/acs5',
    get: ['NAME', 'B01003_001E'],
    for: 'county:*',
    in: 'state:08'
  },
  {
    mode: 'replace_staging',
    targetSheetName: 'STG_Census_CO_Counties'
  }
);
```

### `censusApiHealthCheck()`

Queries the 2024 ACS 5-year endpoint for Colorado and returns a small status object. It does not write to the workbook.

### `censusApiInstallMenu()`

Adds a **Census API** menu. In a mature workbook, call this function from the existing `onOpen()` function rather than defining a second `onOpen()` trigger.

## Provenance and logging

Every fetch returns:

- `fetchedAtUtc`
- `year`
- `dataset`
- `rowCount`
- `columnCount`
- SHA-256 `requestHash`
- `sourceUrlRedacted`
- `cacheHit`

Snapshot metadata is also written as a note on cell `A1`. When an `ExecutionLog` tab exists, the writer appends a compact four-column log row without the API key. Set `writeExecutionLog: false` to suppress that behavior.

## Failure behavior

The connector fails closed when:

- `CENSUS_API_KEY` is absent;
- request fields contain unsafe or unsupported characters;
- more than 50 individual variables are requested;
- the Census endpoint returns non-JSON or malformed row widths;
- a non-retryable HTTP error occurs;
- append headers do not match exactly; or
- `replace_staging` targets a RAW/source-labeled tab.

HTTP `408`, `429`, and `5xx` responses are retried with bounded exponential backoff and jitter. The API key is redacted from raised errors.

## Production handoff

The connector is ready when all of the following are true:

- code is merged;
- the bound Apps Script project contains `CensusApi.gs`;
- `CENSUS_API_KEY` exists in Script Properties;
- `censusApiHealthCheck()` returns `ok: true`;
- one controlled snapshot is captured;
- normalization consumes the snapshot;
- QA and parity pass; and
- the external tracker records completion.
