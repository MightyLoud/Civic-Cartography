# Denton County, Texas — Countywide, Commissioner, and Constable-Precinct Release

## Status

Verified 16-office release with permanent read-only Census and Denton County GIS drift validation. The release contains one countywide Census feature, four official Commissioner precinct features, and six official Constable / Justice-of-the-Peace precinct features.

## Purpose

Denton County proves the Civic Cartography pipeline can represent county government across three distinct geography contracts: multiple countywide offices sharing one feature, four County Commissioners retaining Commissioner precinct geography, and six Constables retaining separate Justice / Constable precinct geography.

## Jurisdiction identity

- Official name: Denton County
- State: Texas
- Jurisdiction type: county
- County FIPS: `121`
- Census GEOID: `48121`
- Representation model: six countywide offices, four Commissioner precinct offices, and six Constable precinct offices
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Commissioner geometry source: Denton County GIS `Commissioner Precincts` (`PoliticalBoundaries_GC/MapServer/4`)
- Stable Commissioner source field: `COMMISH`
- Constable geometry source: Denton County GIS `JP / Constable` (`PoliticalBoundaries_GC/MapServer/5`)
- Stable Constable source field: `JP_C`
- Current Constable source name field: `NAME_CONST`

## Current official scope

| Office | Representative geography | Officeholder | Evidence note |
|---|---|---|---|
| County Judge | Countywide | Andy Eads | Current countywide office |
| Sheriff | Countywide | Tracy Murphree | Current countywide office |
| County Clerk | Countywide | Juli Luke | Current countywide office |
| District Clerk | Countywide | David Trantham | Current countywide office |
| Tax Assessor-Collector | Countywide | Dawn Waye | Current countywide office |
| County Treasurer | Countywide | Cindy Yeatts Brown | Current countywide office |
| Commissioner Precinct 1 | Commissioner Precinct 1 | Ryan Williams | Official GIS `COMMISH = 1` |
| Commissioner Precinct 2 | Commissioner Precinct 2 | Kevin Falconer | Official GIS `COMMISH = 2` |
| Commissioner Precinct 3 | Commissioner Precinct 3 | Bobbie J. Mitchell | Official GIS `COMMISH = 3` |
| Commissioner Precinct 4 | Commissioner Precinct 4 | Dianne Edmondson | Official GIS `COMMISH = 4` |
| Constable Precinct 1 | Constable Precinct 1 | Trevor Krueger | Appointed effective May 29, 2026 after Johnny Hammons resigned; live office page and GIS agree |
| Constable Precinct 2 | Constable Precinct 2 | Michael A. Truitt | Official GIS `JP_C = 2` and `NAME_CONST` match |
| Constable Precinct 3 | Constable Precinct 3 | Dan Rochelle | Official GIS `JP_C = 3` and `NAME_CONST` match |
| Constable Precinct 4 | Constable Precinct 4 | Danny Fletcher | Official GIS `JP_C = 4` and `NAME_CONST` match |
| Constable Precinct 5 | Constable Precinct 5 | Doug Boydston | Official GIS `JP_C = 5` and `NAME_CONST` match |
| Constable Precinct 6 | Constable Precinct 6 | Richard Bachus | Official GIS `JP_C = 6` and `NAME_CONST` match |

## Precinct 1 source transition

Denton County's Elected Officials directory still lists Johnny Hammons as Constable Precinct 1. More current official evidence controls the release:

1. Commissioners Court accepted Hammons's resignation effective May 29, 2026.
2. Commissioners Court approved Trevor Krueger's appointment effective May 29, 2026. The agenda text spells the surname `Kruger`.
3. The live Precinct 1 office page spells the surname `Krueger` and identifies him as Constable.
4. The official `JP / Constable` GIS layer independently records `NAME_CONST = TREVOR KRUEGER`.

The stale directory entry and spelling variance are preserved as QA evidence rather than silently discarded.

## Stable identifiers

```text
TX:county:denton:countywide:COUNTYWIDE        -> denton-county-countywide
TX:county:denton:commissioner_precinct:1     -> denton-county-commissioner-precinct-1
TX:county:denton:commissioner_precinct:2     -> denton-county-commissioner-precinct-2
TX:county:denton:commissioner_precinct:3     -> denton-county-commissioner-precinct-3
TX:county:denton:commissioner_precinct:4     -> denton-county-commissioner-precinct-4
TX:county:denton:constable_precinct:1        -> denton-county-constable-precinct-1
TX:county:denton:constable_precinct:2        -> denton-county-constable-precinct-2
TX:county:denton:constable_precinct:3        -> denton-county-constable-precinct-3
TX:county:denton:constable_precinct:4        -> denton-county-constable-precinct-4
TX:county:denton:constable_precinct:5        -> denton-county-constable-precinct-5
TX:county:denton:constable_precinct:6        -> denton-county-constable-precinct-6
```

The countywide normalized record represents all six countywide offices. Separate normalized rows are required for each Commissioner and Constable precinct because those offices have distinct election geographies. Constables have countywide peace-officer jurisdiction, but they are elected by precinct; their representation geography is therefore the official `JP / Constable` precinct layer, not the countywide polygon.

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 16 |
| Official source records | 23 |
| Scoped offices | 16 |
| Normalized geography rows | 11 |
| Canonical GeoJSON features | 11 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Constable-precinct features | 6 |
| Missing joins | 0 |
| Extra joins | 0 |

All eleven normalized records have `qa_status = approved` and `parity_ok = TRUE`. The combined canonical release SHA-256 is:

```text
775f2e6c66f3c0c1527e563246dda66bc8aa650a40e02050ed6803599e40667a
```

## Release files

- Commissioners Court roster: `data/raw/denton-county/current-commissioners-court.csv`
- Additional countywide constitutional offices: `data/raw/denton-county/current-countywide-constitutional-offices.csv`
- Current Constables: `data/raw/denton-county/current-constables.csv`
- Source manifest: `data/raw/denton-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/denton-county/tigerweb-county-48121.geojson`
- Raw Commissioner precinct snapshot: `data/raw/denton-county/commissioner-precincts-1-4.geojson`
- Raw Constable precinct snapshot: `data/raw/denton-county/constable-precincts-1-6.geojson`
- Countywide and Commissioner normalized records: `data/normalized/denton_county_commissioners_court.csv`
- Constable normalized records: `data/normalized/denton_county_constables.csv`
- Canonical county geometry: `data/geojson/denton_county_countywide.geojson`
- Canonical Commissioner geometry: `data/geojson/denton_county_commissioner_precincts.geojson`
- Canonical Constable geometry: `data/geojson/denton_county_constable_precincts.geojson`

## Source and QA rules

1. Preserve all sixteen scoped current officeholders.
2. Model the County Judge, Sheriff, County Clerk, District Clerk, Tax Assessor-Collector, and County Treasurer as countywide.
3. Model each County Commissioner through the official `Commissioner Precincts` layer and stable field `COMMISH`.
4. Model each Constable through the separate official `JP / Constable` layer and stable field `JP_C`.
5. Require `NAME_CONST` to match the resolved current Constable roster.
6. Preserve the Precinct 1 resignation, appointment, stale-directory conflict, and surname spelling variance.
7. Do not create multiple normalized rows that duplicate the countywide geography join.
8. Do not substitute Commissioner precinct polygons for Constable precinct polygons.
9. Do not map Constables to the countywide polygon merely because their peace-officer jurisdiction extends throughout the county.
10. Do not include Justice-of-the-Peace officeholders in this bounded release.
11. Every normalized record must join exactly one canonical feature.
12. Current-source drift fails CI when geometry, stable source attributes, `COMMISH` IDs, `JP_C` IDs, `NAME_CONST` values, Census GEOID, or canonical joins change.

## Result

Denton County now covers sixteen elected offices with eleven geometries: six countywide offices share one verified county polygon, Commissioners Precincts 1–4 retain four official Commissioner polygons, and Constables Precincts 1–6 retain six separate official Justice / Constable polygons. Permanent read-only validation protects all three geography contracts and the resolved current roster.
