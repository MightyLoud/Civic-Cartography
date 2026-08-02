# Fort Bend County, Texas — Commissioners Court and Countywide Constitutional Offices

## Status

Verified ten-office release package. First-pass pre-merge validation succeeded in Fort Bend County workflow run #47 and repository workflow run #747.

## Purpose

Fort Bend County tests three related civic-data contracts. Commissioner precinct boundaries changed effective January 1, 2026; the current holder of the elected County Judge office is serving an explicitly bounded interim term; and six countywide elected offices must share one county geometry without creating duplicate normalized rows. The release keeps office structure, current selection method, roster, and geometry as separate facts while preserving archived boundaries and a still-live predecessor biography as non-controlling evidence.

## Jurisdiction identity

- Official name: Fort Bend County
- State: Texas
- Jurisdiction type: county
- County FIPS: `157`
- Census GEOID: `48157`
- Representation model: six countywide elected offices plus four Commissioners elected from precincts
- Total scoped elected offices: ten
- Current holders selected by election: nine
- Current interim-appointed holders: one
- Unique current officeholders: ten
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Controlling precinct geometry source: Fort Bend County GIS `InteractiveMap/Boundaries_Public/FeatureServer/7`
- Current precinct effective date: January 1, 2026
- Stable current precinct field: `NAME`
- Stable current precinct values: `1`, `2`, `3`, `4`
- Live current attributes: `COMMISSION`, `WEBSITE`, and `EFFECTIVE`

## Current official scope

| Office | Representative geography | Current holder | Current selection status |
|---|---|---|---|
| County Judge | Countywide | Daniel Wong | Interim appointment through December 31, 2026 |
| Sheriff | Countywide | Eric Fagan | Elected |
| County Clerk | Countywide | Laura Richard | Elected |
| District Clerk | Countywide | Beverley McGrew Walker | Elected |
| Tax Assessor-Collector | Countywide | Carmen P. Turner | Elected |
| County Treasurer | Countywide | Bill Rickert | Elected |
| Commissioner Precinct 1 | Precinct 1 | Vincent Morales Jr. | Elected |
| Commissioner Precinct 2 | Precinct 2 | Grady Prestage | Elected |
| Commissioner Precinct 3 | Precinct 3 | W. A. “Andy” Meyers | Elected |
| Commissioner Precinct 4 | Precinct 4 | Dexter L. McCoy | Elected |

The elected-official directory defines all ten roles as elected county offices. The county homepage separately labels Daniel Wong Interim County Judge, and Commissioners Court recorded his oath for a term from April 13, 2026 through December 31, 2026. The model therefore counts ten elected offices but distinguishes nine current holders selected by election from one current interim-appointed holder.

## Countywide office handling

Six countywide roles share the single Fort Bend County Census feature:

- County Judge — Daniel Wong, interim-appointed current holder
- Sheriff — Eric Fagan
- County Clerk — Laura Richard
- District Clerk — Beverley McGrew Walker
- Tax Assessor-Collector — Carmen P. Turner
- County Treasurer — Bill Rickert

The five newly added offices are separately elected and represented through one shared countywide normalized record. The release does not create additional countywide geometries or duplicate normalized rows.

Each new office is supported by a current official office page and an independent official cross-check:

- Sheriff history lists Eric Fagan as the 45th Sheriff serving from 2021 to present.
- District Clerk biography states that Beverley McGrew Walker is serving her second term.
- The official tax-rate portal independently identifies Carmen Turner for the Fort Bend County Tax Office.
- Treasurer history lists Bill Rickert as serving from 2019 to present.
- The Bail Bond Board roster identifies Bill Rickert as Treasurer and Laura Richard as County Clerk.

## County Judge succession handling

The current County Judge page identifies Daniel Wong, and the county homepage labels him Interim County Judge. An official Commissioners Court agenda records his statement and oath for the bounded term April 13, 2026 through December 31, 2026.

A still-live official page titled `About the Fort Bend County Judge` continues to identify former County Judge KP George. It is retained as stale predecessor evidence and must never override the current Daniel Wong record.

## Geometry source hierarchy

### Controlling January 1, 2026 layer

`https://gisportal.fortbendcountytx.gov/arcgis/rest/services/InteractiveMap/Boundaries_Public/FeatureServer/7`

This official current layer exposes exactly four polygons with stable `NAME` values 1 through 4. Its live attributes identify the four current Commissioners, link each polygon to the corresponding official Commissioner page, and carry `EFFECTIVE = 1767225600000`, equivalent to January 1, 2026.

| Precinct | `COMMISSION` | `WEBSITE` suffix |
|---|---|---|
| 1 | Vincent Morales, Jr. | `commissioner-precinct-1` |
| 2 | Grady Prestage | `commissioner-precinct-2` |
| 3 | Andy Meyers | `commissioner-precinct-3` |
| 4 | Dexter McCoy | `commissioner-precinct-4` |

### Archived 2022–2025 layer

`https://gisportal.fortbendcountytx.gov/arcgis/rest/services/Archive/Archive/FeatureServer/0`

This official archived layer uses stable field `PRECINCT` for values 1 through 4 and is explicitly labeled for 2022 through 2025. Every archived precinct polygon differs from the current January 1, 2026 polygon for the same precinct. It is preserved as historical geometry evidence and does not control the release.

## Source contract

1. The current FeatureServer must remain available and return exactly four polygon features.
2. `NAME` must resolve to values `1`, `2`, `3`, and `4`.
3. Live `COMMISSION`, `WEBSITE`, and `EFFECTIVE` values must match the current court and January 1, 2026 contract.
4. Direct GeoJSON regeneration from the current layer must match the committed raw and canonical snapshots.
5. The archived layer must remain separately identifiable through field `PRECINCT`, and all four archived geometries must remain distinct from the controlling layer unless the source hierarchy is reviewed.
6. Daniel Wong must remain identified as the current interim holder rather than an elected incumbent unless controlling sources change.
7. The stale KP George biography must remain non-controlling predecessor evidence.
8. The elected-office directory and current office pages must identify all ten scoped offices and current holders.
9. The five new constitutional offices must remain countywide and share the existing Census feature.
10. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:fort-bend:countywide:COUNTYWIDE       -> fort-bend-county-countywide
TX:county:fort-bend:commissioner_precinct:1    -> fort-bend-county-commissioner-precinct-1
TX:county:fort-bend:commissioner_precinct:2    -> fort-bend-county-commissioner-precinct-2
TX:county:fort-bend:commissioner_precinct:3    -> fort-bend-county-commissioner-precinct-3
TX:county:fort-bend:commissioner_precinct:4    -> fort-bend-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 10 |
| Official source records | 23 |
| Scoped elected offices | 10 |
| Current holders selected by election | 9 |
| Current interim-appointed holders | 1 |
| Unique current officeholders | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Fort Bend County workflow run #47: success
- Repository workflow run #747: success
- Automated tests: 60 passed
- Normalized datasets validated: 20 files
- Live `NAME`, `COMMISSION`, `WEBSITE`, and `EFFECTIVE` contract: passed
- Four-district January 2026 versus 2022–2025 archive divergence: passed
- Current precinct snapshot comparison: passed
- Current Census snapshot comparison: passed
- Geometry joins: passed
- Geometry changes: 0
- Combined canonical SHA-256: `0b00c8a65accd7841d6ee18612071b5c695d9bf0de05be5e7316a9386d40becc`

## Release files

- Current Commissioners Court roster: `data/raw/fort-bend-county/current-commissioners-court.csv`
- Current countywide constitutional offices: `data/raw/fort-bend-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/fort-bend-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/fort-bend-county/tigerweb-county-48157.geojson`
- Raw current Commissioner precinct snapshot: `data/raw/fort-bend-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/fort_bend_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/fort_bend_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/fort_bend_county_commissioner_precincts.geojson`
- Regression test: `tests/test_fort_bend_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-fort-bend-county.yml`

## Result

Fort Bend County contains ten scoped elected offices represented by five geometries. Six countywide offices share one Census feature, while Commissioners Precincts 1 through 4 retain the official boundaries effective January 1, 2026. Daniel Wong remains explicitly modeled as the current interim-appointed holder of the elected County Judge office. The archived 2022–2025 layer and stale KP George biography remain explicit without controlling the current release.
