# Galveston County, Texas — Effective-Date Cutover and Abolished Treasurer Office

## Status

Release candidate. First-pass Galveston County workflow #19 and repository workflow #1050 passed. Final exact-head validation is pending.

## Purpose

This release proves two transition rules:

1. Commissioner precinct geometry effective June 29, 2026 supersedes older official-looking ArcGIS services.
2. The County Treasurer office was constitutionally abolished effective January 1, 2024 and must not be modeled as a vacancy.

## Current elected scope

| Office | Geography | Current holder |
|---|---|---|
| County Judge | Countywide | Mark A. Henry |
| Commissioner Precinct 1 | Precinct 1 | Darrell Apffel |
| Commissioner Precinct 2 | Precinct 2 | Joe Giusti |
| Commissioner Precinct 3 | Precinct 3 | Hank Dugie |
| Commissioner Precinct 4 | Precinct 4 | Dr. Robin Armstrong |
| Sheriff | Countywide | Jimmy Fullen |
| County Clerk | Countywide | Dwight D. Sullivan |
| District Clerk | Countywide | John D. Kinard |
| Tax Assessor-Collector | Countywide | Cheryl E. Johnson |

All nine holders are current elected incumbents.

## Abolished office contract

- Office: County Treasurer
- Status: abolished
- Effective date: January 1, 2024
- Current officeholder: none
- Vacancy status: not applicable
- Current function destination: Treasury division of the County Clerk

The Texas Constitution and enrolled H.J.R. 134 control the abolition. A stale county staff-directory tag still associates Commissioner Hank Dugie with the former Treasurer's Office; it is preserved as conflict evidence but does not create a vacancy, incumbent, current-office row, or geometry.

## Geometry cutover contract

- Census GEOID: `48167`
- Public Experience item: `e0b0fef416cd42ad991b8ae95d22bb59`
- Experience title: `Galveston Final2`
- Experience owner: `sigler_n`
- Map effective date: June 29, 2026
- Current service: `Galveston_County_Commissioner_Precincts_2026/FeatureServer/0`
- Stable field: `Commission`
- Stable values: `1`, `2`, `3`, `4`

The selected service is linked through the public Experience graph and carries post-cutover item or layer evidence. Older generic Commissioner services are retained as rejected candidates; immutable ArcGIS item timestamps prove at least one predates the cutover.

## Source hierarchy

1. County office pages and the elected-officials directory control the nine-person roster.
2. The Texas Constitution and enrolled H.J.R. 134 control abolition and its effective date.
3. The current Treasury page controls the destination of former Treasurer functions.
4. The county announcement controls the June 29, 2026 map cutover date.
5. The public Experience item controls the map entrypoint.
6. The dedicated 2026 ArcGIS layer controls Commissioner geometry.
7. Census TIGERweb controls the countywide boundary.
8. Stale and pre-cutover sources remain conflict evidence but do not control current records.

## CI source-access behavior

Galveston County's CivicPlus host returns HTTP 403 to GitHub-hosted runners. The permanent workflow attempts those county pages and validates them when accessible. When blocked, it requires the exact committed nine-office roster, one abolished-office record, and 18-source hierarchy. Live gates still require enrolled H.J.R. 134, Experience metadata, the selected layer and values, post-cutover timestamps, rejected legacy-item timestamps, fresh Commissioner geometry, and fresh Census geometry. The Texas Constitution DocViewer is retained as an official source but returns a non-textual shell to CI, so enrolled H.J.R. 134 is the mandatory live legal-text gate.

## Stable identifiers

```text
TX:county:galveston:countywide:COUNTYWIDE    -> galveston-county-countywide
TX:county:galveston:commissioner_precinct:1 -> galveston-county-commissioner-precinct-1
TX:county:galveston:commissioner_precinct:2 -> galveston-county-commissioner-precinct-2
TX:county:galveston:commissioner_precinct:3 -> galveston-county-commissioner-precinct-3
TX:county:galveston:commissioner_precinct:4 -> galveston-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 9 |
| Official source records | 18 |
| Current elected offices | 9 |
| Unique current officeholders | 9 |
| Abolished constitutional offices | 1 |
| Vacancies created for abolished office | 0 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All normalized rows use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- First green Galveston County workflow: #19
- First green repository workflow: #1050
- Automated tests: 82 passed
- Normalized datasets validated: 26 files
- ArcGIS snapshot comparison: passed
- Census snapshot comparison: passed
- Geometry joins: passed
- Combined canonical SHA-256: `61ee037c5540c22cd576cf77c27a5f701f06e0bcd56adf9414962e9a00cc1a06`

## Release files

- `data/raw/galveston-county/current-elected-offices.csv`
- `data/raw/galveston-county/abolished-constitutional-offices.csv`
- `data/raw/galveston-county/source-manifest.csv`
- `data/raw/galveston-county/portal-source-contract.json`
- `data/raw/galveston-county/tigerweb-county-48167.geojson`
- `data/raw/galveston-county/commissioner-precincts-1-4.geojson`
- `data/normalized/galveston_county_elected_offices.csv`
- `data/geojson/galveston_county_countywide.geojson`
- `data/geojson/galveston_county_commissioner_precincts.geojson`
- `tests/test_galveston_county_roster.py`
- `scripts/validate_galveston_sources.py`
- `.github/workflows/validate-galveston-county.yml`
- `.github/workflows/bootstrap-galveston-county.yml` — archived, manual-only, read-only provenance note

## Result

Galveston County contains nine current elected offices represented by five geometries, plus one abolished constitutional office preserved outside the current roster. The proof demonstrates effective-date source precedence and abolished-office modeling without creating a false vacancy or accepting stale geometry.
