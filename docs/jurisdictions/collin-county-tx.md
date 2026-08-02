# Collin County, Texas — Commissioners Court

## Status

Release candidate pending application-layer resolution and final validation.

## Purpose

Collin County tests stale official narrative versus controlling operational GIS. The county's official precinct landing page labels the Commissioner precinct information current but still says the plan was adopted September 6, 2011 and effective January 1, 2012. The county's live GIS layer states that the current Commissioner plan was approved November 1, 2021 under Court Order 2021-1127-11-01 and carries the current four-Commissioner roster in `COMMISH_N`.

## Jurisdiction identity

- Official name: Collin County
- State: Texas
- Jurisdiction type: county
- County FIPS: `085`
- Census GEOID: `48085`
- Representation model: one County Judge elected at large plus four Commissioners elected from equal precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Official current roster page: Collin County Commissioners Court
- Official interactive application: `https://maps.collincountytx.gov/ccmap_commissioners/`
- Stable precinct field: `COMMISH`
- Stable precinct values: `1`, `2`, `3`, `4`
- Live roster field: `COMMISH_N`

## Current official scope

| Office | Representative geography | Current holder |
|---|---|---|
| County Judge | Countywide | Chris Hill |
| County Commissioner Precinct 1 | Precinct 1 | Susan Fletcher |
| County Commissioner Precinct 2 | Precinct 2 | Cheryl Williams |
| County Commissioner Precinct 3 | Precinct 3 | Darrell Hale |
| County Commissioner Precinct 4 | Precinct 4 | Duncan Webb |

The official Commissioners Court page identifies all five current holders. Individual biographies independently support each officeholder.

## Stale narrative and controlling geometry

The official `Precincts and State Districts` page calls its entries current but says the Commissioner precincts were adopted September 6, 2011 and became effective January 1, 2012.

The operational Commissioners layer instead states:

- approved November 1, 2021
- Court Order `2021-1127-11-01`
- polygon geometry
- stable field `COMMISH`
- live roster field `COMMISH_N`

The release preserves the landing-page dates as stale official narrative. The application-resolved 2021 layer controls the geometry and roster-bearing GIS contract.

## Source contract

1. The official Commissioners Court page must identify Chris Hill and Commissioners Susan Fletcher, Cheryl Williams, Darrell Hale, and Duncan Webb.
2. The official precinct landing page's 2011/2012 dates must remain classified as stale narrative unless the county corrects the page.
3. The official `ccmap_commissioners` application must resolve to a Collin County ArcGIS Commissioners layer.
4. The controlling layer must remain polygon geometry with fields `COMMISH` and `COMMISH_N`.
5. `COMMISH` must resolve to exactly 1 through 4.
6. Live `COMMISH_N` values must match the independently maintained current roster.
7. The controlling layer must identify the November 1, 2021 adoption and Court Order `2021-1127-11-01`.
8. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
9. The County Judge must join only to the Census county feature.
10. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:collin:countywide:COUNTYWIDE       -> collin-county-countywide
TX:county:collin:commissioner_precinct:1    -> collin-county-commissioner-precinct-1
TX:county:collin:commissioner_precinct:2    -> collin-county-commissioner-precinct-2
TX:county:collin:commissioner_precinct:3    -> collin-county-commissioner-precinct-3
TX:county:collin:commissioner_precinct:4    -> collin-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 13 |
| Scoped elected offices | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

Pending bootstrap source resolution and final exact-head Collin County and repository-wide workflow results.

## Release files

- Current roster: `data/raw/collin-county/current-commissioners-court.csv`
- Source manifest: `data/raw/collin-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/collin-county/tigerweb-county-48085.geojson`
- Raw Commissioner precinct snapshot: `data/raw/collin-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/collin_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/collin_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/collin_county_commissioner_precincts.geojson`
- Regression test: `tests/test_collin_county_roster.py`

## Result

Collin County will contain five scoped elected offices represented by five geometries. The proof demonstrates that a current official landing page can carry stale adoption dates while a linked operational GIS layer supplies the controlling plan date, stable precinct IDs, current roster attributes, and canonical polygons.
