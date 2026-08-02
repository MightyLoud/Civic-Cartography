# Travis County, Texas — Commissioners Court and Countywide Constitutional Offices

## Status

Release candidate extending the PR #46 Commissioners Court model with five additional countywide offices. Final release requires green Travis County and repository-wide validation, merge, and Jurisdiction Portfolio update.

## Purpose

Travis County is the third county transfer proof and the second proof that multiple countywide constitutional offices can share one verified county geometry. The extension adds five countywide offices without creating duplicate normalized rows or changing the released five-feature geometry package.

## Jurisdiction identity

- Official name: Travis County
- State: Texas
- Jurisdiction type: county
- County FIPS: `453`
- Census GEOID: `48453`
- Representation model: six countywide offices plus four Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct source layer: Travis County GIS `Travis_County_Commissioner_Precincts` (`FeatureServer/0`)
- Precinct geometry transport: ArcGIS Hub cached GeoJSON export for the same official item
- Stable precinct source field: `PRECINCT`
- Declared officeholder field: `COMMISSIONER`
- Current Commissioner roster validation: live layer renderer keyed by `PRECINCT`
- Stable precinct values: `1`, `2`, `3`, `4`

## Current official scope

| Office | Representative geography | Officeholder | Evidence note |
|---|---|---|---|
| County Judge | Countywide | Andy Brown | Existing released countywide office |
| Sheriff | Countywide | Sally Hernandez | Official Travis County Sheriff's Office page |
| County Clerk | Countywide | Dyana Limon-Mercado | Official County Clerk page |
| District Clerk | Countywide | Velva L. Price | Official District Clerk biography |
| Tax Assessor-Collector | Countywide | Celia Israel | Elected November 2024 and sworn January 3, 2025 |
| County Treasurer | Countywide | Dolores Ortega Carter | Official Treasurer page and transparency directory |
| Commissioner Precinct 1 | Precinct 1 | Jeff Travillion | Live GIS renderer and office page |
| Commissioner Precinct 2 | Precinct 2 | Brigid Shea | Live GIS renderer and office page |
| Commissioner Precinct 3 | Precinct 3 | Ann Howard | Live GIS renderer and office page |
| Commissioner Precinct 4 | Precinct 4 | George Morales | Live GIS renderer and office page |

## Tax Assessor-Collector source conflict

Current official evidence identifies Celia Israel as Travis County Tax Assessor-Collector:

1. Israel was elected in November 2024.
2. The Tax Office announced her January 3, 2025 inauguration for a four-year term.
3. The current Tax Office biography and 2026 newsroom identify Israel as Tax Assessor-Collector.
4. The Travis County financial-transparency directory also lists Celia Israel.

A separate official Bruce Elfant biography page remains live and describes Elfant as Tax Assessor-Collector. The release preserves that page as stale-source evidence instead of silently discarding it or allowing it to override newer official records.

## Precinct 4 source conflict

The live Precinct 4 office page, county homepage, public-information directory, and live GIS renderer identify George Morales as Commissioner. The financial-transparency directory still lists Margaret Gomez, and the ArcGIS Hub cached export retains `Margaret Gómez` in the Precinct 4 `COMMISSIONER` property.

The composite raw precinct snapshot preserves the cached value as `HUB_CACHE_COMMISSIONER`, while its current `COMMISSIONER` value is resolved from the live renderer. Direct FeatureServer and MapServer feature queries repeatedly timed out or returned HTTP 503 from GitHub-hosted runners, so the release separates live metadata/renderer validation from cached polygon transport.

## Stable identifiers

```text
TX:county:travis:countywide:COUNTYWIDE       -> travis-county-countywide
TX:county:travis:commissioner_precinct:1    -> travis-county-commissioner-precinct-1
TX:county:travis:commissioner_precinct:2    -> travis-county-commissioner-precinct-2
TX:county:travis:commissioner_precinct:3    -> travis-county-commissioner-precinct-3
TX:county:travis:commissioner_precinct:4    -> travis-county-commissioner-precinct-4
```

## Target parity

| Layer | Count |
|---|---:|
| Commissioners Court evidence rows | 5 |
| New countywide constitutional-office evidence rows | 5 |
| Total current-officeholder evidence rows | 10 |
| Official source records | 19 |
| Scoped offices | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records require `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Commissioners Court roster: `data/raw/travis-county/current-commissioners-court.csv`
- Countywide constitutional-office roster: `data/raw/travis-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/travis-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/travis-county/tigerweb-county-48453.geojson`
- Raw composite Commissioner precinct snapshot: `data/raw/travis-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/travis_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/travis_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/travis_county_commissioner_precincts.geojson`
- Roster and geometry regression test: `tests/test_travis_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-travis-county.yml`

## Source and QA rules

1. Preserve all ten current officeholders.
2. Represent the County Judge, Sheriff, County Clerk, District Clerk, Tax Assessor-Collector, and County Treasurer in one countywide normalized record.
3. Do not create duplicate countywide rows or geometry.
4. Map each Commissioner to exactly one official Commissioner precinct feature.
5. Preserve the stale Bruce Elfant biography, Margaret Gomez directory value, and cached `Margaret Gómez` value as explicit conflict evidence.
6. Require the live GIS renderer roster to match Jeff Travillion, Brigid Shea, Ann Howard, and George Morales.
7. Require the live layer schema to retain `PRECINCT` and `COMMISSIONER`.
8. Do not include County Attorney, District Attorney, Constables, Justices of the Peace, or judicial offices in this bounded extension.
9. Every normalized record must join exactly one canonical feature.
10. Geometry files must remain unchanged in this extension.

## Result

When released, Travis County will contain ten elected offices represented by five verified geometries. Six countywide offices share the one Census county feature, and Commissioners Precincts 1–4 retain their four official precinct features. The extension preserves both the Tax Assessor-Collector and Precinct 4 source conflicts without weakening current-officeholder validation.
