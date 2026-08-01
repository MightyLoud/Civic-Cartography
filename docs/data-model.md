# Normalized Civic Data Model

Normalized datasets are UTF-8 CSV files stored in `data/normalized/`. Use one record per publishable civic geography, district, office, or other mapped unit.

## Required columns

| Column | Type | Rule |
|---|---|---|
| `record_id` | text | Stable, unique identifier. Never reuse an ID for a different entity. |
| `state_fips` | text | Two-digit state FIPS code, including leading zeroes. |
| `state_abbr` | text | Two-letter uppercase postal abbreviation. |
| `jurisdiction_type` | text | `state`, `county`, `municipality`, `school_district`, or `special_district`. |
| `jurisdiction_name` | text | Official or source-supported jurisdiction name. |
| `district_type` | text | District category such as `council`, `commissioner`, `school_board`, `legislative`, or `at_large`. |
| `district_id` | text | Source-supported district identifier; use `AT_LARGE` when applicable. |
| `district_name` | text | Human-readable district label. |
| `source_url` | URL | Direct official or authoritative source URL. |
| `source_retrieved_at` | date | Retrieval date in `YYYY-MM-DD` format. |
| `source_confidence` | text | `high`, `medium`, or `low`. |
| `qa_status` | text | `pending`, `reviewed`, or `approved`. |
| `parity_ok` | boolean text | Must be `TRUE` before publication. |

## Recommended columns

| Column | Purpose |
|---|---|
| `office_name` | Office associated with the district or geography. |
| `election_date` | Relevant election date in `YYYY-MM-DD` format. |
| `geometry_source_url` | Direct source for the boundary geometry. |
| `geometry_id` | Join key used to connect the record to GeoJSON. |
| `parent_record_id` | Stable link to a containing jurisdiction. |
| `notes` | Concise exception, ambiguity, or methodology note. |

## Identifier guidance

Prefer deterministic IDs that survive spelling and formatting changes:

```text
{state_abbr}:{jurisdiction_type}:{jurisdiction_key}:{district_type}:{district_id}
```

Example:

```text
TX:municipality:austin:council:05
```

## Source and confidence rules

- `high`: direct official filing, ordinance, election authority, GIS portal, or government dataset.
- `medium`: authoritative secondary source or official page with incomplete machine-readable detail.
- `low`: unresolved secondary evidence; do not publish without review.

## Geometry contract

Every published record that should appear on a map must have a nonblank `geometry_id` matching exactly one GeoJSON feature. Every publishable GeoJSON feature must resolve back to exactly one normalized record unless the documented model intentionally uses a one-to-many relationship.
