# Travis County, Texas — Commissioners Court

## Status

Release candidate for one countywide County Judge and four Commissioner precincts. Final release requires green permanent drift validation, repository-wide validation, and merge.

## Purpose

Travis County is the third county transfer proof. It tests the county model against an independently maintained ArcGIS Enterprise layer with a slow feature-query endpoint, a live renderer that carries the current roster, a cached geometry export with one stale officeholder value, and a separate official directory that has not caught up with the current Precinct 4 officeholder.

## Jurisdiction identity

- Official name: Travis County
- State: Texas
- Jurisdiction type: county
- County FIPS: `453`
- Census GEOID: `48453`
- Representation model: one County Judge elected countywide plus four Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct source layer: Travis County GIS `Travis_County_Commissioner_Precincts` (`FeatureServer/0`)
- Precinct geometry transport: the ArcGIS Hub cached GeoJSON export for the same official item
- Stable precinct source field: `PRECINCT`
- Declared officeholder field: `COMMISSIONER`
- Current roster validation: the live layer renderer keyed by `PRECINCT`
- Stable precinct values: `1`, `2`, `3`, `4`

## Current official scope

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Andy Brown |
| Commissioner Precinct 1 | Precinct 1 | Jeff Travillion |
| Commissioner Precinct 2 | Precinct 2 | Brigid Shea |
| Commissioner Precinct 3 | Precinct 3 | Ann Howard |
| Commissioner Precinct 4 | Precinct 4 | George Morales |

## Precinct 4 source conflict

The live Precinct 4 office page, county homepage, public-information directory, and live GIS renderer identify George Morales as Commissioner. A separate financial-transparency contact directory still lists Margaret Gomez. The ArcGIS Hub cached export also retains `Margaret Gómez` in its Precinct 4 `COMMISSIONER` property.

The release does not silently discard either stale value. The composite raw precinct snapshot preserves the cached value as `HUB_CACHE_COMMISSIONER`, while its current `COMMISSIONER` value is resolved from the live renderer. The directory conflict remains in the source manifest and roster notes.

Direct FeatureServer and MapServer feature queries repeatedly timed out or returned HTTP 503 from GitHub-hosted validation runners, including filtered geometry and attributes-only requests. The release therefore does not claim that a successful live feature query returned the current officeholder attributes.

## Hybrid GIS source contract

The source and transport responsibilities are separated deliberately:

1. Travis County's official `FeatureServer/0` remains the authoritative source layer.
2. Live layer metadata must expose both `PRECINCT` and `COMMISSIONER` fields.
3. The live unique-value renderer must map Precincts 1–4 to Jeff Travillion, Brigid Shea, Ann Howard, and George Morales.
4. The ArcGIS Hub cached GeoJSON export for the same official item supplies exactly four polygon geometries.
5. Cached officeholder values do not control the current roster; any mismatch is retained as `HUB_CACHE_COMMISSIONER`.
6. The cached Precinct 4 value must remain explicit until the official export catches up or the source contract is re-evaluated.
7. Permanent validation rebuilds the composite snapshot and fails on geometry, schema, renderer roster, precinct identity, cached-conflict handling, or canonical-join drift.

This is a transport adaptation, not a source substitution. The polygons, layer metadata, and renderer all originate from Travis County's official ArcGIS item.

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
| Current-officeholder evidence rows | 5 |
| Official source records | 12 |
| Scoped offices | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records require `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Commissioners Court roster: `data/raw/travis-county/current-commissioners-court.csv`
- Source manifest: `data/raw/travis-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/travis-county/tigerweb-county-48453.geojson`
- Raw composite Commissioner precinct snapshot: `data/raw/travis-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/travis_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/travis_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/travis_county_commissioner_precincts.geojson`
- Roster and geometry regression test: `tests/test_travis_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-travis-county.yml`

## Source and QA rules

1. Preserve all five current officeholders.
2. Map the County Judge only to the countywide Census feature.
3. Map each Commissioner to exactly one official Commissioner precinct feature.
4. Require exactly four precinct values: `1`, `2`, `3`, and `4`.
5. Require the live GIS renderer roster to match Jeff Travillion, Brigid Shea, Ann Howard, and George Morales.
6. Require the live layer schema to retain `PRECINCT` and `COMMISSIONER`.
7. Preserve the Margaret Gomez directory value and cached `Margaret Gómez` value as outdated evidence.
8. Do not include Constables, Justices of the Peace, or other county offices in this bounded release.
9. Every normalized record must join exactly one canonical feature.
10. Current-source drift fails CI when Census geometry, precinct geometry, schema, renderer roster, cached-conflict handling, precinct IDs, or canonical joins change.

## Result

When released, Travis County will contain five elected offices represented by five verified geometries: one countywide Census feature for the County Judge and four official Commissioner precinct features. The release preserves both Precinct 4 stale-source conflicts and documents the hybrid official-source contract required for reliable automated validation.
