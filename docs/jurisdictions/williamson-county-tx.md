# Williamson County, Texas — Commissioners Court Transfer Proof

## Purpose

Williamson County is the second county-level Civic Cartography proof. It tests whether the Denton County Commissioners Court pattern transfers cleanly to an independent official GIS stack with different source fields.

## Jurisdiction identity

- Official name: Williamson County
- State: Texas
- Jurisdiction type: county
- County FIPS: `491`
- Census GEOID: `48491`
- Governing body: Commissioners Court
- Representation model: one County Judge elected countywide and four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Williamson County GIS `Commissioner, Constable, JP Precincts` (`public/county_elections/MapServer/1`)
- Stable precinct source field: `PCT_NUMBER`

## Current official roster

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Steven Snell |
| Commissioner Precinct 1 | Precinct 1 | Terry Cook |
| Commissioner Precinct 2 | Precinct 2 | Cynthia Long |
| Commissioner Precinct 3 | Precinct 3 | Valerie Covey |
| Commissioner Precinct 4 | Precinct 4 | Russ Boles |

## Planned stable identifiers

```text
TX:county:williamson:countywide:COUNTYWIDE        -> williamson-county-countywide
TX:county:williamson:commissioner_precinct:1     -> williamson-county-commissioner-precinct-1
TX:county:williamson:commissioner_precinct:2     -> williamson-county-commissioner-precinct-2
TX:county:williamson:commissioner_precinct:3     -> williamson-county-commissioner-precinct-3
TX:county:williamson:commissioner_precinct:4     -> williamson-county-commissioner-precinct-4
```

## Target parity

| Layer | Expected count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 9 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Preserve all five current Commissioners Court members.
2. Model the County Judge as countywide and each Commissioner as precinct-based.
3. Use the Census county feature for GEOID `48491`.
4. Use Williamson County GIS `public/county_elections/MapServer/1` for precinct geometry.
5. Resolve precincts through stable source field `PCT_NUMBER` and require IDs 1–4 exactly once.
6. Do not reuse Denton County's `COMMISH` schema or any Denton-specific attributes.
7. Keep raw source responses separate from canonical map-ready GeoJSON.
8. Every normalized record must join exactly one canonical feature.
9. Current-source drift must fail CI when geometry, stable source attributes, precinct IDs, GEOID, or canonical joins change.
10. Constables, Justices of the Peace, and other county offices remain outside this bounded release.

## Completion rule

Williamson County is not complete until the five-member roster, one county boundary, four official precinct boundaries, five normalized records, five canonical features, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
