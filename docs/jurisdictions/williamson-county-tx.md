# Williamson County, Texas — Countywide and Shared Commissioner / Constable / JP Precincts

## Status

Verified eighteen-office release validated in Williamson County workflow run #36 and repository workflow run #343. Four Constables and four Justices of the Peace were added to the existing four shared precinct records without changing normalized-row or geometry counts.

## Purpose

Williamson County first proved that the Denton County Commissioners Court pattern transfers to an independent GIS stack. The countywide extension then proved six offices can share one Census feature. This extension proves three separate elected office families can share each of four official precinct features without duplicate rows or invented polygons.

## Jurisdiction identity

- Official name: Williamson County
- State: Texas
- Jurisdiction type: county
- County FIPS: `491`
- Census GEOID: `48491`
- Representation model: six countywide offices plus four shared Commissioner / Constable / Justice-of-the-Peace precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Williamson County GIS `Commissioner, Constable, JP Precincts` (`public/county_elections/MapServer/1`)
- Stable queryable precinct source field: `LABEL_NAME`
- Stable query values: `PCT 1`, `PCT 2`, `PCT 3`, `PCT 4`

## Source-schema finding

The ArcGIS renderer references field `PCT_NUMBER`, but that field is not exposed in the layer's queryable field list or feature attributes. The API exposes `LABEL_NAME` values `PCT 1` through `PCT 4` and `COUNTY = WILLIAMSON`. The release uses that actual query contract and preserves the renderer/query inconsistency as source evidence.

## Current official scope

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Steven Snell |
| Sheriff | Countywide | Matthew Lindemann |
| County Clerk | Countywide | Nancy E. Rister |
| District Clerk | Countywide | Lisa David |
| Tax Assessor-Collector | Countywide | Catherine Totty |
| County Treasurer | Countywide | D. Scott Heselmeyer |
| Commissioner Precinct 1 | Shared Precinct 1 | Terry Cook |
| Constable Precinct 1 | Shared Precinct 1 | Mickey Chance |
| Justice of the Peace Precinct 1 | Shared Precinct 1 | KT Musselman |
| Commissioner Precinct 2 | Shared Precinct 2 | Cynthia Long |
| Constable Precinct 2 | Shared Precinct 2 | Jeff Anderson |
| Justice of the Peace Precinct 2 | Shared Precinct 2 | Angela Williams |
| Commissioner Precinct 3 | Shared Precinct 3 | Valerie Covey |
| Constable Precinct 3 | Shared Precinct 3 | Kevin Wilkie |
| Justice of the Peace Precinct 3 | Shared Precinct 3 | Evelyn McLean |
| Commissioner Precinct 4 | Shared Precinct 4 | Russ Boles |
| Constable Precinct 4 | Shared Precinct 4 | Paul Leal |
| Justice of the Peace Precinct 4 | Shared Precinct 4 | Rhonda Redden |

## Shared precinct contract

Williamson County publishes one official four-feature layer named `Commissioner, Constable, JP Precincts`. Each precinct feature therefore represents three paired elected offices. The normalized model keeps one row per official geography:

```text
Precinct 1 -> Commissioner Terry Cook + Constable Mickey Chance + JP KT Musselman
Precinct 2 -> Commissioner Cynthia Long + Constable Jeff Anderson + JP Angela Williams
Precinct 3 -> Commissioner Valerie Covey + Constable Kevin Wilkie + JP Evelyn McLean
Precinct 4 -> Commissioner Russ Boles + Constable Paul Leal + JP Rhonda Redden
```

Creating separate rows or polygons for the paired offices would duplicate the same official geometry and inflate join counts.

## Tax Assessor-Collector transition

Williamson County's Elected Officials directory still lists Larry Gaddes. More current official evidence controls the current-holder field:

1. Commissioners Court accepted Gaddes's resignation in June 2026.
2. Commissioners Court appointed Catherine Totty on July 14, 2026, effective July 21.
3. The live Tax Office page identifies Catherine Totty as the current Tax Assessor-Collector.

The stale directory entry and complete transition trail remain preserved as QA evidence.

## Stable identifiers

```text
TX:county:williamson:countywide:COUNTYWIDE        -> williamson-county-countywide
TX:county:williamson:commissioner_precinct:1     -> williamson-county-commissioner-precinct-1
TX:county:williamson:commissioner_precinct:2     -> williamson-county-commissioner-precinct-2
TX:county:williamson:commissioner_precinct:3     -> williamson-county-commissioner-precinct-3
TX:county:williamson:commissioner_precinct:4     -> williamson-county-commissioner-precinct-4
```

The identifiers remain unchanged because this extension adds offices to existing geography records rather than creating new geography.

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 18 |
| Official source records | 26 |
| Scoped offices | 18 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Shared Commissioner / Constable / JP features | 4 |
| Geometry changes | 0 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records retain `qa_status = approved` and `parity_ok = TRUE`. Thirty-one automated tests passed. The combined canonical release SHA-256 remains:

```text
4670b4dd07affbfd098a6fd63716ed78b08bba71d8c5740bb8b19f1838b37d34
```

## Release files

- Commissioners Court roster: `data/raw/williamson-county/current-commissioners-court.csv`
- Countywide constitutional offices: `data/raw/williamson-county/current-countywide-constitutional-offices.csv`
- Current Constables: `data/raw/williamson-county/current-constables.csv`
- Current Justices of the Peace: `data/raw/williamson-county/current-justices-of-the-peace.csv`
- Source manifest: `data/raw/williamson-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/williamson-county/tigerweb-county-48491.geojson`
- Raw shared-precinct snapshot: `data/raw/williamson-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/williamson_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/williamson_county_countywide.geojson`
- Canonical shared-precinct geometry: `data/geojson/williamson_county_commissioner_precincts.geojson`
- Countywide roster and transition test: `tests/test_williamson_countywide_roster.py`
- Shared precinct roster test: `tests/test_williamson_jp_constable_roster.py`

## Source and QA rules

1. Preserve all eighteen scoped current officeholders.
2. Model six countywide offices through one Census county feature.
3. Model each Commissioner, paired Constable, and paired Justice of the Peace through the same official precinct feature.
4. Do not create duplicate normalized rows or polygons for paired offices.
5. Require `LABEL_NAME = PCT 1` through `PCT 4` and `COUNTY = WILLIAMSON` on the official precinct features.
6. Preserve the renderer/query field inconsistency rather than claiming hidden `PCT_NUMBER` is queryable.
7. Preserve the Gaddes resignation, Totty appointment, and stale-directory conflict.
8. Preserve all five canonical features unchanged in this extension.
9. Every normalized record must join exactly one canonical feature.
10. Current-source drift fails CI when geometry, source labels, county attributes, GEOID, or canonical joins change.
11. County Attorney, District Attorney, county courts, district courts, Auditor, and appointed administrative offices remain outside scope.

## Result

Williamson County now covers eighteen elected offices with five geometries: six countywide offices share one verified Census county feature, while each of four official precinct features serves its paired Commissioner, Constable, and Justice of the Peace. The extension added eight officeholders and ten authoritative sources without changing geometry, normalized-row count, join count, or the canonical digest.
