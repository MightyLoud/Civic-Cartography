# Denton County, Texas — Countywide and Commissioner-Precinct Release

## Status

Verified ten-office release validated in Denton County workflow run #18 and repository workflow run #267. The release contains one countywide Census feature plus four official commissioner-precinct features. Five additional countywide constitutional officeholders were added without changing geometry.

## Purpose

Denton County proves the Civic Cartography pipeline can represent county government with multiple offices sharing one countywide feature while four commissioners retain separate precinct geography.

## Jurisdiction identity

- Official name: Denton County
- State: Texas
- Jurisdiction type: county
- County FIPS: `121`
- Census GEOID: `48121`
- Representation model: six countywide offices plus four precinct-based County Commissioners
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Denton County GIS `2022 Commissioner Precincts` (`PoliticalBoundaries_GC/MapServer/4`)
- Stable precinct source field: `COMMISH`

## Current official scope

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Andy Eads |
| Sheriff | Countywide | Tracy Murphree |
| County Clerk | Countywide | Juli Luke |
| District Clerk | Countywide | David Trantham |
| Tax Assessor-Collector | Countywide | Dawn Waye |
| County Treasurer | Countywide | Cindy Yeatts Brown |
| Commissioner Precinct 1 | Precinct 1 | Ryan Williams |
| Commissioner Precinct 2 | Precinct 2 | Kevin Falconer |
| Commissioner Precinct 3 | Precinct 3 | Bobbie J. Mitchell |
| Commissioner Precinct 4 | Precinct 4 | Dianne Edmondson |

## Stable identifiers

```text
TX:county:denton:countywide:COUNTYWIDE        -> denton-county-countywide
TX:county:denton:commissioner_precinct:1     -> denton-county-commissioner-precinct-1
TX:county:denton:commissioner_precinct:2     -> denton-county-commissioner-precinct-2
TX:county:denton:commissioner_precinct:3     -> denton-county-commissioner-precinct-3
TX:county:denton:commissioner_precinct:4     -> denton-county-commissioner-precinct-4
```

The countywide normalized record represents all six countywide offices. Separate normalized rows for each countywide office are intentionally not created because they would duplicate the same geography join.

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 10 |
| Official source records | 12 |
| Scoped offices | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records retain `qa_status = approved` and `parity_ok = TRUE`. The geometry files are unchanged from the Commissioners Court release, so the combined canonical release SHA-256 remains:

```text
2d514e6a297d020445e54d32731428dda030ca1543924195ecee6d6d020d37c3
```

## Release files

- Commissioners Court roster: `data/raw/denton-county/current-commissioners-court.csv`
- Additional countywide constitutional offices: `data/raw/denton-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/denton-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/denton-county/tigerweb-county-48121.geojson`
- Raw commissioner-precinct snapshot: `data/raw/denton-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/denton_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/denton_county_countywide.geojson`
- Canonical precinct geometry: `data/geojson/denton_county_commissioner_precincts.geojson`

## Source and QA rules

1. Preserve all ten scoped current officeholders.
2. Model the County Judge, Sheriff, County Clerk, District Clerk, Tax Assessor-Collector, and County Treasurer as countywide.
3. Model each County Commissioner as precinct-based.
4. Do not create multiple normalized rows that duplicate the countywide geometry join.
5. Use the official Census county feature for GEOID `48121`.
6. Use Denton County GIS item `2022 Commissioner Precincts`; the historic pre-2022 layer is not an acceptable current source.
7. Resolve commissioner precincts through stable source field `COMMISH` and require IDs 1–4 exactly once.
8. Every normalized record joins exactly one canonical feature.
9. Current-source drift fails CI when geometry, stable source attributes, precinct IDs, GEOID, or canonical joins change.
10. The Criminal District Attorney, judges, constables, justices of the peace, auditor, and appointed offices remain outside this bounded release.

## Result

Denton County now covers ten elected offices with five geometries: six countywide offices share one verified county polygon, while Commissioners Precincts 1–4 retain four official precinct polygons. Permanent read-only validation confirms the constitutional-office extension did not alter the released geometry or join contract.
