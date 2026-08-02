# Williamson County, Texas — Commissioners Court Release

## Status

Verified second county-level release with permanent read-only Census and Williamson County GIS drift validation.

## Purpose

Williamson County proves the Denton County Commissioners Court pattern transfers cleanly to an independent county GIS stack without hard-coded Denton fields or county-specific fetch logic.

## Jurisdiction identity

- Official name: Williamson County
- State: Texas
- Jurisdiction type: county
- County FIPS: `491`
- Census GEOID: `48491`
- Governing body: Commissioners Court
- Representation model: one County Judge elected countywide and four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Williamson County GIS `Commissioner, Constable, JP Precincts` (`public/county_elections/MapServer/1`)
- Stable queryable precinct source field: `LABEL_NAME`
- Stable query values: `PCT 1`, `PCT 2`, `PCT 3`, `PCT 4`

## Source-schema finding

The ArcGIS renderer references field `PCT_NUMBER`, but that field is not exposed in the layer's queryable field list or feature attributes. The API exposes `LABEL_NAME` values `PCT 1` through `PCT 4` and `COUNTY = WILLIAMSON`. The release uses that actual query contract and preserves the renderer/query inconsistency as source evidence.

## Current official roster

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Steven Snell |
| Commissioner Precinct 1 | Precinct 1 | Terry Cook |
| Commissioner Precinct 2 | Precinct 2 | Cynthia Long |
| Commissioner Precinct 3 | Precinct 3 | Valerie Covey |
| Commissioner Precinct 4 | Precinct 4 | Russ Boles |

## Released stable identifiers

```text
TX:county:williamson:countywide:COUNTYWIDE        -> williamson-county-countywide
TX:county:williamson:commissioner_precinct:1     -> williamson-county-commissioner-precinct-1
TX:county:williamson:commissioner_precinct:2     -> williamson-county-commissioner-precinct-2
TX:county:williamson:commissioner_precinct:3     -> williamson-county-commissioner-precinct-3
TX:county:williamson:commissioner_precinct:4     -> williamson-county-commissioner-precinct-4
```

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 9 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records have `qa_status = approved` and `parity_ok = TRUE`. The combined canonical release SHA-256 is:

```text
4670b4dd07affbfd098a6fd63716ed78b08bba71d8c5740bb8b19f1838b37d34
```

## Release files

- Current roster: `data/raw/williamson-county/current-commissioners-court.csv`
- Source manifest: `data/raw/williamson-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/williamson-county/tigerweb-county-48491.geojson`
- Raw commissioner-precinct snapshot: `data/raw/williamson-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/williamson_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/williamson_county_countywide.geojson`
- Canonical precinct geometry: `data/geojson/williamson_county_commissioner_precincts.geojson`

## Source and QA rules

1. Preserve all five current Commissioners Court members.
2. Model the County Judge as countywide and each Commissioner as precinct-based.
3. Use the Census county feature for GEOID `48491`.
4. Use Williamson County GIS `public/county_elections/MapServer/1` for precinct geometry.
5. Resolve precincts through queryable source field `LABEL_NAME` and require `PCT 1` through `PCT 4` exactly once.
6. Require `COUNTY = WILLIAMSON` on all four source features.
7. Preserve the renderer/query field inconsistency rather than claiming hidden `PCT_NUMBER` is queryable.
8. Do not reuse Denton County's `COMMISH` schema or any Denton-specific attributes.
9. Every normalized record joins exactly one canonical feature.
10. Current-source drift fails CI when geometry, source labels, county attributes, GEOID, or canonical joins change.
11. Constables, Justices of the Peace, and other county offices remain outside this bounded release.

## Result

Williamson County confirms the county template transfers across independent source schemas: the same reusable Census and ArcGIS machinery produced one countywide feature, four commissioner-precinct features, five approved joins, and permanent live-source drift protection without modifying the generic fetchers.
