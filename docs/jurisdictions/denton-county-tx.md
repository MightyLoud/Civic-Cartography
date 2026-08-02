# Denton County, Texas — Commissioners Court Proof

## Purpose

Denton County is the Civic Cartography proof for a county governing body with mixed countywide and precinct representation. The bounded scope is the five-member Commissioners Court.

## Jurisdiction identity

- Official name: Denton County
- State: Texas
- Jurisdiction type: county
- County FIPS: `121`
- Census GEOID: `48121`
- Governing body: Commissioners Court
- Representation model: one County Judge elected countywide and four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: official Denton County GIS service, pending exact ArcGIS layer verification

## Current official roster

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Andy Eads |
| Commissioner Precinct 1 | Precinct 1 | Ryan Williams |
| Commissioner Precinct 2 | Precinct 2 | Kevin Falconer |
| Commissioner Precinct 3 | Precinct 3 | Bobbie J. Mitchell |
| Commissioner Precinct 4 | Precinct 4 | Dianne Edmondson |

## Planned stable identifiers

```text
TX:county:denton:countywide:COUNTYWIDE        -> denton-county-countywide
TX:county:denton:commissioner_precinct:1     -> denton-county-commissioner-precinct-1
TX:county:denton:commissioner_precinct:2     -> denton-county-commissioner-precinct-2
TX:county:denton:commissioner_precinct:3     -> denton-county-commissioner-precinct-3
TX:county:denton:commissioner_precinct:4     -> denton-county-commissioner-precinct-4
```

## Target parity

| Layer | Expected count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Preserve all five current Commissioners Court members.
2. Model the County Judge as countywide and each Commissioner as precinct-based.
3. Use the official Census county feature for GEOID `48121`.
4. Use only an official Denton County GIS service for commissioner-precinct geometry.
5. Do not derive or trace polygon geometry from printed PDF maps.
6. Keep raw source responses separate from canonical map-ready GeoJSON.
7. Every normalized record must join exactly one canonical feature.
8. Current-source drift must fail CI when geometry, stable source attributes, precinct IDs, GEOID, or canonical joins change.
9. Other county constitutional, judicial, constable, and justice-of-the-peace offices remain outside this bounded release.

## Completion rule

Denton County is not complete until the official roster, one county boundary, four commissioner-precinct boundaries, five normalized records, five canonical features, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
