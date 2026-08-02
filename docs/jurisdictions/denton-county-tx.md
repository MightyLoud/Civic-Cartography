# Denton County, Texas — Commissioners Court Release

## Status

Release candidate validated with permanent read-only Census and Denton County GIS drift checks. The bounded release covers the complete five-member Commissioners Court.

## Purpose

Denton County is the Civic Cartography proof for a county governing body with mixed countywide and precinct representation.

## Jurisdiction identity

- Official name: Denton County
- State: Texas
- Jurisdiction type: county
- County FIPS: `121`
- Census GEOID: `48121`
- Governing body: Commissioners Court
- Representation model: one County Judge elected countywide and four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Denton County GIS `2022 Commissioner Precincts` (`PoliticalBoundaries_GC/MapServer/4`)
- Stable precinct source field: `COMMISH`

## Current official roster

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Andy Eads |
| Commissioner Precinct 1 | Precinct 1 | Ryan Williams |
| Commissioner Precinct 2 | Precinct 2 | Kevin Falconer |
| Commissioner Precinct 3 | Precinct 3 | Bobbie J. Mitchell |
| Commissioner Precinct 4 | Precinct 4 | Dianne Edmondson |

## Released stable identifiers

```text
TX:county:denton:countywide:COUNTYWIDE        -> denton-county-countywide
TX:county:denton:commissioner_precinct:1     -> denton-county-commissioner-precinct-1
TX:county:denton:commissioner_precinct:2     -> denton-county-commissioner-precinct-2
TX:county:denton:commissioner_precinct:3     -> denton-county-commissioner-precinct-3
TX:county:denton:commissioner_precinct:4     -> denton-county-commissioner-precinct-4
```

## Completed parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 6 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records have `qa_status = approved` and `parity_ok = TRUE`. The combined canonical release SHA-256 is:

```text
2d514e6a297d020445e54d32731428dda030ca1543924195ecee6d6d020d37c3
```

## Release files

- Current roster: `data/raw/denton-county/current-commissioners-court.csv`
- Source manifest: `data/raw/denton-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/denton-county/tigerweb-county-48121.geojson`
- Raw commissioner-precinct snapshot: `data/raw/denton-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/denton_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/denton_county_countywide.geojson`
- Canonical precinct geometry: `data/geojson/denton_county_commissioner_precincts.geojson`

## Source and QA rules

1. Preserve all five current Commissioners Court members.
2. Model the County Judge as countywide and each Commissioner as precinct-based.
3. Use the official Census county feature for GEOID `48121`.
4. Use Denton County GIS item `2022 Commissioner Precincts`; the historic pre-2022 layer is not an acceptable current source.
5. Resolve commissioner precincts through stable source field `COMMISH` and require IDs 1–4 exactly once.
6. Do not derive or trace polygon geometry from printed PDF maps.
7. Keep raw source responses separate from canonical map-ready GeoJSON.
8. Every normalized record must join exactly one canonical feature.
9. Current-source drift fails CI when geometry, stable source attributes, precinct IDs, GEOID, or canonical joins change.
10. Other county constitutional, judicial, constable, and justice-of-the-peace offices remain outside this bounded release.

## Result

Denton County now proves one county governing body can combine a countywide presiding office and four precinct-based members while preserving official source lineage and exact one-to-one geometry joins.
