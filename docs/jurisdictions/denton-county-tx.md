# Denton County, Texas — Countywide, Commissioner, and JP / Constable Release

## Status

Verified 22-office release validated in Denton County workflow run #50 and repository workflow run #299. Permanent read-only validation protects one Census county feature, four official Commissioner precincts, and six official `JP / Constable` precincts.

## Purpose

Denton County proves the pipeline can represent multiple elected offices sharing geography without duplicating normalized rows or polygons.

## Jurisdiction identity

- Official name: Denton County
- State: Texas
- Jurisdiction type: county
- County FIPS: `121`
- Census GEOID: `48121`
- Representation model: six countywide offices, four Commissioner precinct offices, and twelve paired Justice-of-the-Peace / Constable offices on six shared precincts
- County geometry: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Commissioner geometry: Denton County GIS `Commissioner Precincts` (`PoliticalBoundaries_GC/MapServer/4`)
- Commissioner key: `COMMISH`
- Shared JP / Constable geometry: Denton County GIS `JP / Constable` (`PoliticalBoundaries_GC/MapServer/5`)
- Shared precinct key: `JP_C`
- Constable name field: `NAME_CONST`
- Justice-of-the-Peace name field: `NAME_JP`

## Current official scope

### Countywide offices

| Office | Officeholder |
|---|---|
| County Judge | Andy Eads |
| Sheriff | Tracy Murphree |
| County Clerk | Juli Luke |
| District Clerk | David Trantham |
| Tax Assessor-Collector | Dawn Waye |
| County Treasurer | Cindy Yeatts Brown |

### Commissioner precincts

| Precinct | Commissioner |
|---:|---|
| 1 | Ryan Williams |
| 2 | Kevin Falconer |
| 3 | Bobbie J. Mitchell |
| 4 | Dianne Edmondson |

### Shared Justice-of-the-Peace / Constable precincts

| Precinct | Justice of the Peace | Constable |
|---:|---|---|
| 1 | Alan Wheeler | Trevor Krueger |
| 2 | James R. DePiazza | Michael A. Truitt |
| 3 | James Kerbow | Dan Rochelle |
| 4 | Harris Hughey | Danny Fletcher |
| 5 | Mike Oglesby | Doug Boydston |
| 6 | Blanca Oliver | Richard Bachus |

The Justice of the Peace and Constable for each numbered precinct share one official `JP / Constable` polygon. Each pair is therefore represented by one normalized geography row and one canonical feature.

## Precinct 1 Constable transition

Denton County's Elected Officials directory still lists Johnny Hammons as Constable Precinct 1. More current official evidence controls the release:

1. Commissioners Court accepted Hammons's resignation effective May 29, 2026.
2. Commissioners Court approved Trevor Krueger's appointment effective May 29, 2026. The agenda text spells the surname `Kruger`.
3. The live Precinct 1 office page spells the surname `Krueger`.
4. The official GIS layer records `NAME_CONST = TREVOR KRUEGER`.

The stale directory entry and spelling variance remain preserved as QA evidence.

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

The stable `constable_precinct` identifiers are retained because they already anchor the released shared precinct geometry. The normalized `office_name` and evidence explicitly include both paired offices.

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 22 |
| Official source records | 30 |
| Scoped offices | 22 |
| Normalized geography rows | 11 |
| Canonical GeoJSON features | 11 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Shared JP / Constable features | 6 |
| Missing joins | 0 |
| Extra joins | 0 |
| Automated tests | 29 |

All normalized records retain `qa_status = approved` and `parity_ok = TRUE`. This extension adds no geometry, so the combined canonical release SHA-256 remains:

```text
775f2e6c66f3c0c1527e563246dda66bc8aa650a40e02050ed6803599e40667a
```

## Release files

- Commissioners Court roster: `data/raw/denton-county/current-commissioners-court.csv`
- Countywide constitutional offices: `data/raw/denton-county/current-countywide-constitutional-offices.csv`
- Current Constables: `data/raw/denton-county/current-constables.csv`
- Current Justices of the Peace: `data/raw/denton-county/current-justices-of-the-peace.csv`
- Source manifest: `data/raw/denton-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/denton-county/tigerweb-county-48121.geojson`
- Raw Commissioner snapshot: `data/raw/denton-county/commissioner-precincts-1-4.geojson`
- Raw shared JP / Constable snapshot: `data/raw/denton-county/constable-precincts-1-6.geojson`
- Countywide and Commissioner normalized records: `data/normalized/denton_county_commissioners_court.csv`
- Shared JP / Constable normalized records: `data/normalized/denton_county_constables.csv`
- Canonical county geometry: `data/geojson/denton_county_countywide.geojson`
- Canonical Commissioner geometry: `data/geojson/denton_county_commissioner_precincts.geojson`
- Canonical shared precinct geometry: `data/geojson/denton_county_constable_precincts.geojson`

## Source and QA rules

1. Preserve all 22 scoped current officeholders.
2. Keep six countywide offices on one county feature.
3. Keep four Commissioners on four `COMMISH` precinct features.
4. Pair each Justice of the Peace and Constable on one shared `JP_C` feature.
5. Require committed and live `NAME_CONST` and `NAME_JP` values to match the resolved rosters.
6. Do not create duplicate normalized rows or geometry features for Justice-of-the-Peace offices.
7. Preserve the Precinct 1 Constable transition and stale-source conflict.
8. Every normalized record must join exactly one canonical feature.
9. Current-source drift fails CI when geometry, stable source attributes, officeholder fields, precinct IDs, Census GEOID, or joins change.

## Validation

- Denton County workflow run #50: passed
- Repository workflow run #299: passed
- Arlington regression run #77: passed
- Irving regression run #129: passed
- Oak Point regression run #107: passed
- CFBISD regression run #92: passed

## Result

Denton County now covers 22 elected offices with 11 geometries: six countywide offices share one county polygon, four Commissioners retain separate Commissioner precincts, and six Justice-of-the-Peace / Constable pairs share six official precinct polygons. The added Justice-of-the-Peace offices increased office coverage without increasing geography rows, features, or the canonical digest.
