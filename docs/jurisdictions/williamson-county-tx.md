# Williamson County, Texas — Commissioners Court and Countywide Constitutional Offices

## Status

Verified ten-office release validated in Williamson County workflow run #23 and repository workflow run #330. Five additional countywide constitutional offices were added without changing the released five-feature geometry package.

## Purpose

Williamson County first proved the Denton County Commissioners Court pattern transfers cleanly to an independent county GIS stack. This extension proves the shared-countywide-office pattern also transfers without duplicate normalized rows or additional geometry.

## Jurisdiction identity

- Official name: Williamson County
- State: Texas
- Jurisdiction type: county
- County FIPS: `491`
- Census GEOID: `48491`
- Representation model: six countywide offices plus four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Williamson County GIS `Commissioner, Constable, JP Precincts` (`public/county_elections/MapServer/1`)
- Stable queryable precinct source field: `LABEL_NAME`
- Stable query values: `PCT 1`, `PCT 2`, `PCT 3`, `PCT 4`

## Source-schema finding

The ArcGIS renderer references field `PCT_NUMBER`, but that field is not exposed in the layer's queryable field list or feature attributes. The API exposes `LABEL_NAME` values `PCT 1` through `PCT 4` and `COUNTY = WILLIAMSON`. The release uses that actual query contract and preserves the renderer/query inconsistency as source evidence.

## Current official scope

| Office | Representative geography | Officeholder | Evidence note |
|---|---|---|---|
| County Judge | Countywide | Steven Snell | Existing released countywide office |
| Sheriff | Countywide | Matthew Lindemann | Live official Sheriff's Office page |
| County Clerk | Countywide | Nancy E. Rister | Live official County Clerk page |
| District Clerk | Countywide | Lisa David | Live official District Clerk page |
| Tax Assessor-Collector | Countywide | Catherine Totty | Appointed effective July 21, 2026 after Larry Gaddes resigned |
| County Treasurer | Countywide | D. Scott Heselmeyer | Live official Treasurer page |
| Commissioner Precinct 1 | Precinct 1 | Terry Cook | Official GIS `LABEL_NAME = PCT 1` |
| Commissioner Precinct 2 | Precinct 2 | Cynthia Long | Official GIS `LABEL_NAME = PCT 2` |
| Commissioner Precinct 3 | Precinct 3 | Valerie Covey | Official GIS `LABEL_NAME = PCT 3` |
| Commissioner Precinct 4 | Precinct 4 | Russ Boles | Official GIS `LABEL_NAME = PCT 4` |

## Tax Assessor-Collector transition

Williamson County's Elected Officials directory still lists Larry Gaddes. More current official evidence controls the current-holder field:

1. Commissioners Court accepted Gaddes's resignation in June 2026.
2. Commissioners Court appointed Catherine Totty on July 14, 2026, effective July 21.
3. The live Tax Office page identifies Catherine Totty as the current Tax Assessor-Collector.

The stale directory entry and the complete transition trail are preserved as QA evidence rather than silently overwritten.

## Stable identifiers

```text
TX:county:williamson:countywide:COUNTYWIDE        -> williamson-county-countywide
TX:county:williamson:commissioner_precinct:1     -> williamson-county-commissioner-precinct-1
TX:county:williamson:commissioner_precinct:2     -> williamson-county-commissioner-precinct-2
TX:county:williamson:commissioner_precinct:3     -> williamson-county-commissioner-precinct-3
TX:county:williamson:commissioner_precinct:4     -> williamson-county-commissioner-precinct-4
```

The countywide normalized record represents all six countywide offices. Separate normalized rows for each countywide office are intentionally not created because they would duplicate the same geography join.

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 10 |
| Official source records | 16 |
| Scoped offices | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Geometry changes | 0 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records retain `qa_status = approved` and `parity_ok = TRUE`. Thirty automated tests passed. The combined canonical release SHA-256 remains:

```text
4670b4dd07affbfd098a6fd63716ed78b08bba71d8c5740bb8b19f1838b37d34
```

## Release files

- Commissioners Court roster: `data/raw/williamson-county/current-commissioners-court.csv`
- Additional countywide constitutional offices: `data/raw/williamson-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/williamson-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/williamson-county/tigerweb-county-48491.geojson`
- Raw commissioner-precinct snapshot: `data/raw/williamson-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/williamson_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/williamson_county_countywide.geojson`
- Canonical precinct geometry: `data/geojson/williamson_county_commissioner_precincts.geojson`
- Roster and transition test: `tests/test_williamson_countywide_roster.py`

## Source and QA rules

1. Preserve all ten scoped current officeholders.
2. Model the County Judge, Sheriff, County Clerk, District Clerk, Tax Assessor-Collector, and County Treasurer as countywide.
3. Model each County Commissioner through the official precinct layer and queryable field `LABEL_NAME`.
4. Preserve the Gaddes resignation, Totty appointment, and stale-directory conflict.
5. Do not create multiple normalized rows that duplicate the countywide geography join.
6. Preserve all five canonical features unchanged in this extension.
7. Require `COUNTY = WILLIAMSON` on all four precinct source features.
8. Preserve the renderer/query field inconsistency rather than claiming hidden `PCT_NUMBER` is queryable.
9. Every normalized record joins exactly one canonical feature.
10. Current-source drift fails CI when geometry, source labels, county attributes, GEOID, or canonical joins change.
11. County Attorney, District Attorney, judges, Constables, Justices of the Peace, Auditor, and appointed administrative offices remain outside this bounded release.

## Result

Williamson County now covers ten elected offices with five geometries: six countywide offices share one verified Census county polygon, while Commissioners Precincts 1–4 retain four official Williamson County GIS polygons. The countywide-office pattern transferred without geometry changes, duplicate joins, or generic-fetcher modifications, while the Gaddes-to-Totty transition remains fully traceable.
