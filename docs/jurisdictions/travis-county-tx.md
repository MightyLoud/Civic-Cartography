# Travis County, Texas — Commissioners Court

## Status

Release candidate for one countywide County Judge and four Commissioner precincts. Final release requires committed official geometry snapshots, green permanent drift validation, repository-wide validation, and merge.

## Purpose

Travis County is the third county transfer proof. It tests the county model against an independently maintained ArcGIS Enterprise layer with a current officeholder attribute, a slow live geometry endpoint, and a conflicting official directory that has not yet caught up with the current Precinct 4 officeholder.

## Jurisdiction identity

- Official name: Travis County
- State: Texas
- Jurisdiction type: county
- County FIPS: `453`
- Census GEOID: `48453`
- Representation model: one County Judge elected countywide plus four Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Travis County GIS `Travis_County_Commissioner_Precincts`
- Stable precinct source field: `PRECINCT`
- Current officeholder source field: `COMMISSIONER`
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

The live Precinct 4 office page, county homepage, public-information directory, and current GIS identify George Morales as Commissioner. A separate financial-transparency contact directory still lists Margaret Gomez. The release preserves that directory as outdated source evidence instead of silently deleting the conflict or allowing it to override the more current official sources.

The GIS layer also contains mixed update state: its current renderer and `COMMISSIONER` attribute identify George Morales, while one editing-template label still references Margaret Gomez. Current feature attributes control the normalized officeholder field; the stale template remains documented as QA evidence.

## Geometry transport finding

The official county FeatureServer and equivalent MapServer expose the correct four polygons, but unfiltered and filtered live GeoJSON queries repeatedly timed out or returned HTTP 503 from GitHub-hosted validation runners. The release therefore uses the ArcGIS Hub cached GeoJSON export for the same Travis County map-service item as its snapshot transport, while retaining the county MapServer as the authoritative source layer.

This is a transport decision, not a source substitution:

1. The source item is Travis County's official current Commissioner Precincts dataset.
2. The cached export is generated from that official map-service item.
3. `PRECINCT` and `COMMISSIONER` remain required in every fetched feature.
4. The four current officeholder values must match the resolved roster.
5. Permanent validation fails if the cached official export changes geometry, precinct identity, current officeholder attributes, or join identifiers.

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
- Raw Commissioner precinct snapshot: `data/raw/travis-county/commissioner-precincts-1-4.geojson`
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
5. Require current `COMMISSIONER` attributes to match Jeff Travillion, Brigid Shea, Ann Howard, and George Morales.
6. Preserve the Margaret Gomez directory and template references as outdated evidence.
7. Do not include Constables, Justices of the Peace, or other county offices in this bounded release.
8. Every normalized record must join exactly one canonical feature.
9. Current-source drift fails CI when geometry, GEOID, precinct IDs, current officeholder attributes, or canonical joins change.

## Result

When released, Travis County will contain five elected offices represented by five verified geometries: one countywide Census feature for the County Judge and four official Commissioner precinct features. The release preserves the Precinct 4 source conflict and documents the cached-export transport required for reliable automated validation.
