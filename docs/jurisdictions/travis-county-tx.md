# Travis County, Texas — Commissioners Court Transfer Proof

## Status

Release target. The official simplified precinct layer and Census county feature have passed live build acquisition; publication remains blocked until the complete release package is validated.

## Purpose

Travis County is the third county-level Civic Cartography proof. It tests whether the countywide-plus-four-precinct model transfers to an independent ArcGIS schema with a live officeholder attribute, a slow detailed service, and documented stale-directory and stale-renderer conflicts.

## Jurisdiction identity

- Official name: Travis County
- State: Texas
- Jurisdiction type: county
- County FIPS: `453`
- Census GEOID: `48453`
- Governing body: Commissioners Court
- Representation model: one County Judge elected countywide and four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Current detailed precinct metadata source: Travis County GIS `Travis_County_Commissioner_Precincts` (`MapServer/0`)
- Published precinct geometry source: Travis County GIS `Admin_Boundaries_Simple` (`MapServer/0`)
- Stable precinct source field: `PRECINCT`
- Live officeholder source attribute: `COMMISSIONER`

## Current official roster

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Andy Brown |
| Commissioner Precinct 1 | Precinct 1 | Jeff Travillion |
| Commissioner Precinct 2 | Precinct 2 | Brigid Shea |
| Commissioner Precinct 3 | Precinct 3 | Ann Howard |
| Commissioner Precinct 4 | Precinct 4 | George Morales |

## Source-resolution findings

The live Precinct 4 page, current county directory, current detailed GIS metadata, and live simplified-layer attributes identify George Morales as current Commissioner. The financial-transparency directory still lists Margaret Gomez, and stale renderer text also survives in one GIS metadata view. Both stale records are preserved but do not control the current-holder field.

The detailed precinct service repeatedly returned ArcGIS wait-timeout errors for geometry, including one-precinct native-JSON requests. Travis County's official simplified service has the same countywide extent, returns the four current precinct geometries promptly, and exposes the current `COMMISSIONER` values. The release therefore separates current detailed metadata from the official simplified geometry source instead of masking the timeout with indefinite retries.

## Planned stable identifiers

```text
TX:county:travis:countywide:COUNTYWIDE        -> travis-county-countywide
TX:county:travis:commissioner_precinct:1     -> travis-county-commissioner-precinct-1
TX:county:travis:commissioner_precinct:2     -> travis-county-commissioner-precinct-2
TX:county:travis:commissioner_precinct:3     -> travis-county-commissioner-precinct-3
TX:county:travis:commissioner_precinct:4     -> travis-county-commissioner-precinct-4
```

## Target parity

| Layer | Expected count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 11 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Preserve all five current Commissioners Court members.
2. Model the County Judge as countywide and each Commissioner as precinct-based.
3. Use the Census county feature for GEOID `48453`.
4. Use the current detailed service for current schema and officeholder metadata.
5. Use the official simplified service for the four published precinct geometries.
6. Resolve precincts through `PRECINCT` and require IDs 1–4 exactly once.
7. Require live `COMMISSIONER` attributes to match Travillion, Shea, Howard, and Morales.
8. Preserve the Margaret Gomez directory and renderer records as stale-source conflicts.
9. Preserve the detailed-service timeout evidence; do not replace it with unbounded retries.
10. Keep raw responses separate from canonical map-ready GeoJSON.
11. Every normalized record must join exactly one canonical feature.
12. Current-source drift must fail CI when geometry, precinct IDs, officeholder attributes, GEOID, or canonical joins change.
13. Constables, Justices of the Peace, and other county offices remain outside this bounded release.

## Completion rule

Travis County is not complete until the five-member roster, one county boundary, four official precinct boundaries, five normalized records, five canonical features, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
