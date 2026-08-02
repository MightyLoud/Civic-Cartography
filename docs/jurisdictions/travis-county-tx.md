# Travis County, Texas — Commissioners Court Transfer Proof

## Status

Release target. Geometry remains unpublished until the official Travis County MapServer and Census county feature pass read-only build validation.

## Purpose

Travis County is the third county-level Civic Cartography proof. It tests whether the countywide-plus-four-precinct model transfers to an independent ArcGIS schema with a live officeholder attribute and a documented stale-directory conflict.

## Jurisdiction identity

- Official name: Travis County
- State: Texas
- Jurisdiction type: county
- County FIPS: `453`
- Census GEOID: `48453`
- Governing body: Commissioners Court
- Representation model: one County Judge elected countywide and four County Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Travis County GIS `Travis_County_Commissioner_Precincts` (`MapServer/0`)
- Stable precinct source field: `PRECINCT`
- Live officeholder source attribute: `COMMISSIONER`
- Source-interface note: the equivalent FeatureServer timed out during the initial build; the official MapServer query interface is used instead

## Current official roster

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Andy Brown |
| Commissioner Precinct 1 | Precinct 1 | Jeff Travillion |
| Commissioner Precinct 2 | Precinct 2 | Brigid Shea |
| Commissioner Precinct 3 | Precinct 3 | Ann Howard |
| Commissioner Precinct 4 | Precinct 4 | George Morales |

## Precinct 4 source conflict

The live Precinct 4 office page, current Travis County elected/appointed-official directory, county homepage, and official GIS identify George Morales as current Commissioner. The county financial-transparency contact directory still lists Margaret Gomez. The stale directory record is preserved as source evidence but does not control the current-holder field.

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
| Official source records | 10 |
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
4. Use Travis County GIS `MapServer/0` for precinct geometry.
5. Resolve precincts through `PRECINCT` and require IDs 1–4 exactly once.
6. Require the live `COMMISSIONER` attributes to match Jeff Travillion, Brigid Shea, Ann Howard, and George Morales.
7. Preserve the Margaret Gomez directory entry as a stale-source conflict.
8. Preserve the initial FeatureServer timeout as source-interface evidence; do not disguise it with longer timeouts.
9. Keep raw source responses separate from canonical map-ready GeoJSON.
10. Every normalized record must join exactly one canonical feature.
11. Current-source drift must fail CI when geometry, precinct IDs, officeholder attributes, GEOID, or canonical joins change.
12. Constables, Justices of the Peace, and other county offices remain outside this bounded release.

## Completion rule

Travis County is not complete until the five-member roster, one county boundary, four official precinct boundaries, five normalized records, five canonical features, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
