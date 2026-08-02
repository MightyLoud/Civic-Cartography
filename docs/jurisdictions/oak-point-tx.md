# Oak Point, Texas — Multi-Seat Top-N Election Proof

## Purpose

Oak Point is the Civic Cartography proof for a contested multi-seat election in which one at-large candidate field fills multiple seats. The bounded scope is the May 2, 2026 election for three City Council members.

## Jurisdiction identity

- Official name: City of Oak Point
- State: Texas
- County context: Denton County
- Jurisdiction type: municipality
- Geometry model: one incorporated-place feature
- Election model: five candidates competing for three at-large seats; the three highest vote-getters are elected
- Term model: two-year staggered council terms
- Geometry source: U.S. Census Bureau TIGERweb Current Incorporated Places (`MapServer/28`)
- Expected Census GEOID: `4853130`, subject to live-fetch verification

## Certified May 2, 2026 result

| Rank | Candidate | Votes | Result |
|---:|---|---:|---|
| 1 | John Lusk | 286 | Elected |
| 2 | Kirk Hawrysio | 285 | Elected |
| 3 | Scott Dufford | 270 | Elected |
| 4 | Kevin Highlander | 217 | Not elected |
| 5 | Justin Cross | 188 | Not elected |

The official canvass certified Lusk, Hawrysio, and Dufford to two-year terms. All five candidate rows remain part of the election evidence.

## Stable identifiers

```text
record_id:   TX:municipality:oak-point:at_large:CITYWIDE
geometry_id: oak-point-citywide
```

## Target parity

| Layer | Expected count |
|---|---:|
| Candidate/result evidence rows | 5 |
| Seats filled | 3 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Preserve all five candidates and the exact certified ranking.
2. Preserve the three-seat cutoff as election logic, not as three independent contests.
3. Preserve the two unsuccessful candidates below the cutoff.
4. Do not create separate council polygons; Oak Point council members are elected at large.
5. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
6. The canonical feature must carry `geometry_id = oak-point-citywide` and matching `record_id`.
7. Current-source drift must fail CI when geometry, GEOID, stable source attributes, or the canonical join changes.
8. The simultaneous sales-tax proposition remains outside this bounded council release.

## Completion rule

Oak Point is not complete until the certified candidate ranking, raw Census geometry, one normalized record, one canonical feature, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
