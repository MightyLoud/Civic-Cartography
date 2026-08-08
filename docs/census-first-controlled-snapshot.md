# First controlled Census RAW snapshot

## Decision

The first API-backed snapshot is a deliberately small, useful geography table:

| Field | Value |
|---|---|
| Required bound workbook | `Nested Divisions` |
| Required spreadsheet ID | `139NETp-iofSoHtl_-IdSSph6xf_ePFVtR8l6KWYadSI` |
| Census vintage | 2024 |
| Dataset | ACS 5-year detailed tables (`acs/acs5`) |
| Geography | All places in Colorado (`for=place:*`, `in=state:08`) |
| Requested variables | `NAME`, `B01003_001E` |
| Census-returned identity fields | `state`, `place` |
| Write mode | Immutable timestamped RAW sheet |
| Cache | Disabled for the capture |

The returned header contract is:

```text
NAME | B01003_001E | state | place
```

The Census Bureau describes the 2024 ACS 5-year dataset as covering all places and released the 2020–2024 estimates on January 29, 2026.

## Why this is the first snapshot

- It exercises authenticated Census API access without a large request.
- It produces stable state/place identifiers useful for deterministic joins.
- It tests leading-zero preservation for Colorado FIPS `08` and five-digit place codes.
- It adds one useful population attribute without pretending ACS estimates are legal-government authority.
- It stays separate from the approved TIGER/Line 2025 geography authority contract.

This snapshot is evidence and enrichment. It does not replace the current TIGER/Line source authority, GEOIDFQ identity rules, publication disposition, or existing normalization pipeline.

## Installation

The Apps Script project must be opened from the exact authoritative workbook:

```text
Nested Divisions
https://docs.google.com/spreadsheets/d/139NETp-iofSoHtl_-IdSSph6xf_ePFVtR8l6KWYadSI/edit
```

Use **Extensions → Apps Script** from that workbook. The project must contain both files:

```text
CensusApi.gs
CensusFirstSnapshot.gs
```

The Script Property below must already exist:

```text
CENSUS_API_KEY = <activated key>
```

## Binding check

Before any Census request, run:

```text
censusApiBindingCheckToUi
```

Expected result:

```text
Census binding — PASS
Expected: Nested Divisions (139NETp-iofSoHtl_-IdSSph6xf_ePFVtR8l6KWYadSI)
Observed: Nested Divisions (139NETp-iofSoHtl_-IdSSph6xf_ePFVtR8l6KWYadSI)
```

The binding guard compares the live spreadsheet ID, not only the title. If the script is attached to any other spreadsheet, it fails before calling the Census API or creating a sheet.

## Run

Only after the binding check passes, run:

```text
censusApiCreateFirstControlledSnapshotToUi
```

The function:

1. requires the exact Nested Divisions spreadsheet ID;
2. performs a live authenticated API request with cache disabled;
3. creates a new timestamped sheet beginning with `_RAW_Census_ACS5_2024_CO_Places_Population`;
4. writes the header and rows as text;
5. preserves the API request hash and redacted source URL in metadata;
6. verifies row and column parity;
7. verifies exact headers;
8. requires every row to have state FIPS `08`;
9. requires every place ID to be five digits and unique;
10. requires nonblank names and nonnegative integer population estimates;
11. requires zero formulas in the RAW snapshot; and
12. appends a key-free QA result to the existing `ExecutionLog` tab.

## Expected success alert

```text
Census RAW snapshot — PASS
Workbook: Nested Divisions (139NETp-iofSoHtl_-IdSSph6xf_ePFVtR8l6KWYadSI)
Sheet: _RAW_Census_ACS5_2024_CO_Places_Population_YYYYMMDD_HHMMSS
Rows: <API row count>
Unique places: <same count>
Content SHA-256: <hash>
Fetched: <UTC timestamp>
```

## Fail-closed behavior

### Wrong workbook

The function raises an error beginning with:

```text
Wrong bound spreadsheet. No Census request or sheet write was attempted.
```

No API request, RAW tab, or execution-log row is created in the wrong workbook.

### Snapshot QA failure

A failed QA run does not delete or overwrite the captured sheet. The timestamped RAW snapshot remains as auditable evidence, `ExecutionLog` receives a `CENSUS_API_SNAPSHOT_QA` failure row, and the function raises an error naming the failed checks.

Do not normalize or publish a failed snapshot. Resolve the exact failed check, capture a new timestamped snapshot, and preserve the failed attempt as evidence.

## Completion contract

The first snapshot is complete only when:

```text
RAW snapshot exists
→ snapshot QA passes
→ normalized consumer is explicitly defined
→ joins validate against stable Census identifiers
→ downstream QA and parity pass
→ tracker records completion
```

Creating the RAW sheet alone does not complete any downstream civic-data row.
