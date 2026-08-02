# Collin County, Texas — Commissioners Court and Countywide Constitutional Offices

## Status

Verified nine-office release package. First-pass pre-merge validation succeeded in Collin County workflow run #34 and repository workflow run #865.

## Purpose

Collin County tests four related civic-data contracts. The county's official precinct landing page labels Commissioner precinct information current but still says the plan was adopted September 6, 2011 and effective January 1, 2012. Browser network capture of the official `ccmap_commissioners` application resolves released geometry to `InteractiveMap/Election/MapServer/1`, while a synchronized Plan C2333 layer records approval on November 1, 2021 under Court Order `2021-1127-11-01`. Five countywide elected offices must share one county geometry without duplicate normalized rows, and the County Treasurer must be represented as an abolished constitutional office rather than a vacancy.

## Jurisdiction identity

- Official name: Collin County
- State: Texas
- Jurisdiction type: county
- County FIPS: `085`
- Census GEOID: `48085`
- Representation model: five countywide elected offices plus four Commissioners elected from equal precincts
- Total scoped elected offices: nine
- Current holders selected by election: nine
- Unique current officeholders: nine
- Abolished constitutional offices: one County Treasurer office
- County Treasurer abolition: Texas Proposition 4, adopted November 6, 1984
- Current treasury-function home: County Clerk Treasury division
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Official current roster pages: Collin County Commissioners Court and County Officials
- Official interactive application: `https://maps.collincountytx.gov/ccmap_commissioners/`
- App-resolved operational layer: `https://maps.collincountytx.gov/server/rest/services/InteractiveMap/Election/MapServer/1`
- Adoption-metadata cross-check: `https://maps.collincountytx.gov/server/rest/services/Election/VotingPrecincts_Edited_PlanC2333/FeatureServer/3`
- Stable precinct field: `COMMISH`
- Stable precinct values: `1`, `2`, `3`, `4`
- Live roster field: `COMMISH_N`
- Source label casing: uppercase officeholder names

## Current official scope

| Office | Representative geography | Current holder | Current status |
|---|---|---|---|
| County Judge | Countywide | Chris Hill | Elected |
| Sheriff | Countywide | Jim Skinner | Elected |
| County Clerk | Countywide | Stacey Kemp | Elected |
| District Clerk | Countywide | Michael Gould | Elected |
| Tax Assessor-Collector | Countywide | Scott Grigg | Elected |
| County Commissioner Precinct 1 | Precinct 1 | Susan Fletcher | Elected |
| County Commissioner Precinct 2 | Precinct 2 | Cheryl Williams | Elected |
| County Commissioner Precinct 3 | Precinct 3 | Darrell Hale | Elected |
| County Commissioner Precinct 4 | Precinct 4 | Duncan Webb | Elected |
| County Treasurer | Not applicable | None | Office abolished in 1984 |

The official Commissioners Court page identifies the five court members. The County Officials directory, department pages, current 2026 materials, and transactional portals identify the four additional countywide holders. All nine scoped current holders are elected incumbents.

## Countywide office handling

Five current countywide roles share the single Collin County Census feature:

- County Judge — Chris Hill
- Sheriff — Jim Skinner
- County Clerk — Stacey Kemp
- District Clerk — Michael Gould
- Tax Assessor-Collector — Scott Grigg

The four newly added offices are separately elected and represented through the existing countywide normalized record. The release does not create additional countywide geometries or duplicate normalized rows.

Each new current office has official evidence and at least one independent official cross-check:

- The Sheriff biography, 2026 media releases, and Bail Bond Board identify Jim Skinner.
- The County Clerk homepage, records form, County Officials directory, Bail Bond Board, and current Commissioners Court agendas identify Stacey Kemp.
- The County Officials directory and current 2026 Auditor agenda material identify Michael Gould.
- The current tax portal, County Officials directory, and January 2025 county announcement identify Scott Grigg.

## Abolished County Treasurer exception

Texas voters adopted Proposition 4 on November 6, 1984, abolishing the office of County Treasurer in Bexar and Collin Counties. Collin County therefore has no Treasurer vacancy, interim holder, or current elected Treasurer office.

The County Clerk's Treasury division currently accounts for county monies, deposits funds into the correct accounts, processes disbursements directed by the County Auditor and Commissioners Court, and reconciles treasury bank accounts. This is a functional division within the elected County Clerk's office, not a separate elected office.

The release keeps three concepts distinct:

1. the historical constitutional office was abolished;
2. no current Treasurer officeholder record exists;
3. treasury functions continue within the County Clerk organization.

## Stale narrative and controlling geometry

The official `Precincts and State Districts` page calls its entries current but says the Commissioner precincts were adopted September 6, 2011 and became effective January 1, 2012.

Browser-level network capture proves the official interactive map requests:

`https://maps.collincountytx.gov/server/rest/services/InteractiveMap/Election/MapServer/1`

That operational layer supplies:

- polygon geometry
- stable `COMMISH` values 1 through 4
- live uppercase `COMMISH_N` officeholder labels

A synchronized official plan-metadata layer supplies:

- approval date November 1, 2021
- Court Order `2021-1127-11-01`
- the same `COMMISH` and `COMMISH_N` schema

The release preserves the landing-page dates as stale official narrative. The app-resolved MapServer layer controls released geometry; the Plan C2333 layer independently controls the adoption metadata.

## Source contract

1. The official Commissioners Court page must identify Chris Hill and Commissioners Susan Fletcher, Cheryl Williams, Darrell Hale, and Duncan Webb.
2. Current official sources must identify Jim Skinner, Stacey Kemp, Michael Gould, and Scott Grigg in their elected roles.
3. Texas legislative history must continue to identify the November 6, 1984 abolition of the Collin County Treasurer office.
4. The County Clerk Treasury page must remain classified as a functional assignment, not a separate elected office.
5. The official precinct landing page's 2011/2012 dates must remain classified as stale narrative unless the county corrects the page.
6. The official `ccmap_commissioners` application must resolve to `InteractiveMap/Election/MapServer/1` or an explicitly reviewed replacement.
7. The operational layer must remain polygon geometry with fields `COMMISH` and `COMMISH_N`.
8. `COMMISH` must resolve to exactly 1 through 4.
9. Live `COMMISH_N` values must match the independently maintained current roster case-insensitively while their source casing remains preserved.
10. The synchronized Plan C2333 layer must identify the November 1, 2021 adoption and Court Order `2021-1127-11-01`.
11. Direct GeoJSON regeneration from the operational layer must match the committed raw and canonical snapshots.
12. The five current countywide offices must share the existing Census feature.
13. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:collin:countywide:COUNTYWIDE       -> collin-county-countywide
TX:county:collin:commissioner_precinct:1    -> collin-county-commissioner-precinct-1
TX:county:collin:commissioner_precinct:2    -> collin-county-commissioner-precinct-2
TX:county:collin:commissioner_precinct:3    -> collin-county-commissioner-precinct-3
TX:county:collin:commissioner_precinct:4    -> collin-county-commissioner-precinct-4
```

The abolished County Treasurer has no current `record_id`, officeholder row, normalized row, or geometry.

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 9 |
| Official source records | 24 |
| Scoped elected offices | 9 |
| Current holders selected by election | 9 |
| Unique current officeholders | 9 |
| Abolished constitutional offices | 1 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Geometry changes | 0 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Collin County workflow run #34: success
- Repository workflow run #865: success
- Automated tests: 74 passed
- Normalized datasets validated: 22 files
- Four countywide current-officeholder evidence rows: passed
- Abolished County Treasurer structural exception: passed
- County Clerk Treasury functional-assignment distinction: passed
- Stale landing-page narrative validation: passed
- Operational layer and uppercase roster contract: passed
- 2021 plan-adoption metadata validation: passed
- Current Commissioner precinct snapshot comparison: passed
- Current Census snapshot comparison: passed
- Geometry joins: passed
- Combined canonical SHA-256: `329729e91a3f0664ff9186002639b4ca76ea53797fbca7d11df983e869244d85`

## Release files

- Current Commissioners Court roster: `data/raw/collin-county/current-commissioners-court.csv`
- Current countywide constitutional offices: `data/raw/collin-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/collin-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/collin-county/tigerweb-county-48085.geojson`
- Raw Commissioner precinct snapshot: `data/raw/collin-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/collin_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/collin_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/collin_county_commissioner_precincts.geojson`
- Regression test: `tests/test_collin_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-collin-county.yml`

## Result

Collin County contains nine scoped elected offices represented by five geometries. Five current countywide offices share one Census feature. Commissioner Precincts 1 through 4 retain the app-resolved operational polygons, stale-narrative distinction, uppercase roster attributes, and 2021 adoption metadata. The County Treasurer remains explicitly modeled as an abolished constitutional office rather than a vacancy.
