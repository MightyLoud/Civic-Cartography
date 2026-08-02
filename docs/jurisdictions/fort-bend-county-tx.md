# Fort Bend County, Texas — Commissioners Court

## Status

Verified release package. Pre-merge validation succeeded in Fort Bend County workflow run #4 and repository workflow run #704.

## Purpose

Fort Bend County tests two related civic-data transitions. The Commissioner precinct boundaries changed effective January 1, 2026, and the current holder of the elected County Judge office is serving an explicitly bounded interim term. The release keeps the office structure, current selection method, roster, and geometry as separate facts while preserving archived boundaries and a still-live predecessor biography as non-controlling evidence.

## Jurisdiction identity

- Official name: Fort Bend County
- State: Texas
- Jurisdiction type: county
- County FIPS: `157`
- Census GEOID: `48157`
- Representation model: one elected County Judge office represented countywide plus four Commissioners elected from precincts
- Current court holders selected by election: four
- Current interim-appointed holders: one
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
| Commissioner Precinct 1 | Precinct 1 | Vincent Morales Jr. | Elected |
| Commissioner Precinct 2 | Precinct 2 | Grady Prestage | Elected |
| Commissioner Precinct 3 | Precinct 3 | W. A. “Andy” Meyers | Elected |
| Commissioner Precinct 4 | Precinct 4 | Dexter L. McCoy | Elected |

The elected-official directory defines all five offices as elected county offices. The county homepage separately labels Daniel Wong Interim County Judge, and Commissioners Court recorded his oath for a term from April 13, 2026 through December 31, 2026. The model therefore counts five elected offices but distinguishes four currently elected holders from one current interim-appointed holder.

## County Judge succession handling

The current County Judge page identifies Daniel Wong, and the county homepage labels him Interim County Judge. An official Commissioners Court agenda records his statement and oath for the bounded term April 13, 2026 through December 31, 2026.

A still-live official page titled `About the Fort Bend County Judge` continues to identify former County Judge KP George. It is retained as stale predecessor evidence and must never override the current Daniel Wong record.

## Geometry source hierarchy

### Controlling January 1, 2026 layer

`https://gisportal.fortbendcountytx.gov/arcgis/rest/services/InteractiveMap/Boundaries_Public/FeatureServer/7`

This official current layer exposes exactly four polygons with stable `NAME` values 1 through 4. Its live attributes identify the four current Commissioners, link each polygon to the corresponding official Commissioner page, and carry `EFFECTIVE = 1767225600000`, equivalent to January 1, 2026.

The live roster rendering is:

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
5. The archived layer must remain separately identifiable through field `PRECINCT` and all four archived geometries must remain distinct from the controlling layer unless the source hierarchy is reviewed.
6. Daniel Wong must remain identified as the current interim holder rather than an elected incumbent unless controlling sources change.
7. The stale KP George biography must remain non-controlling predecessor evidence.
8. The County Judge must join only to the Census county feature.
9. Every normalized row must join exactly one canonical feature.

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
| Current-officeholder evidence rows | 5 |
| Official source records | 13 |
| Scoped elected offices | 5 |
| Current holders selected by election | 4 |
| Current interim-appointed holders | 1 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Fort Bend County workflow run #4: success
- Repository workflow run #704: success
- Automated tests: 58 passed
- Normalized datasets validated: 20 files
- Live `NAME`, `COMMISSION`, `WEBSITE`, and `EFFECTIVE` contract: passed
- Four-district January 2026 versus 2022–2025 archive divergence: passed
- Current precinct snapshot comparison: passed
- Current Census snapshot comparison: passed
- Geometry joins: passed
- Combined canonical SHA-256: `0b00c8a65accd7841d6ee18612071b5c695d9bf0de05be5e7316a9386d40becc`

## Release files

- Current roster: `data/raw/fort-bend-county/current-commissioners-court.csv`
- Source manifest: `data/raw/fort-bend-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/fort-bend-county/tigerweb-county-48157.geojson`
- Raw current Commissioner precinct snapshot: `data/raw/fort-bend-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/fort_bend_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/fort_bend_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/fort_bend_county_commissioner_precincts.geojson`
- Regression test: `tests/test_fort_bend_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-fort-bend-county.yml`

## Result

Fort Bend County contains five scoped elected offices represented by five geometries. The County Judge joins to one countywide Census feature while Daniel Wong is explicitly modeled as the current interim holder. Commissioners Precincts 1 through 4 join to the official boundaries effective January 1, 2026. The archived 2022–2025 layer and stale KP George biography remain explicit without controlling the current release.
