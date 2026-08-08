# First controlled Census RAW snapshot

## Decision

The first API-backed snapshot is a deliberately small, useful geography table:

| Field | Value |
|---|---|
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

The bound Apps Script project must contain both files:

```text
CensusApi.gs
CensusFirstSnapshot.gs
```

The Script Property below must already exist:

```text
CENSUS_API_KEY = <activated key>
```

## Run

From the Apps Script function dropdown, run:

```text
censusApiCreateFirstControlledSnapshotToUi
```

The function:

1. performs a live authenticated API request with cache disabled;
2. creates a new timestamped sheet beginning with `_RAW_Census_ACS5_2024_CO_Places_Population`;
3. writes the header and rows as text;
4. preserves the API request hash and redacted source URL in metadata;
5. verifies row and column parity;
6. verifies exact headers;
7. requires every row to have state FIPS `08`;
8. requires every place ID to be five digits and unique;
9. requires nonblank names and nonnegative integer population estimates;
10. requires zero formulas in the RAW snapshot; and
11. appends a key-free QA result to the existing `ExecutionLog` tab.

## Expected success alert

```text
Census RAW snapshot — PASS
Sheet: _RAW_Census_ACS5_2024_CO_Places_Population_YYYYMMDD_HHMMSS
Rows: <API row count>
Unique places: <same count>
Content SHA-256: <hash>
Fetched: <UTC timestamp>
```

## Fail-closed behavior

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
