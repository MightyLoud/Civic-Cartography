# Carrollton-Farmers Branch ISD — Cumulative-Voting Proof

## Purpose

Carrollton-Farmers Branch Independent School District is the Civic Cartography proof for a contested cumulative-voting election. The bounded scope is the May 2, 2026 election for two at-large Board of Trustees positions.

## Jurisdiction identity

- Official name: Carrollton-Farmers Branch Independent School District
- State: Texas
- County context: Dallas and Denton counties
- Jurisdiction type: school district
- Geometry model: one unified-school-district feature
- Election model: four candidates competing for two districtwide seats using cumulative voting
- Term model: three-year trustee terms
- Geometry source: U.S. Census Bureau TIGERweb Current Unified School Districts (`MapServer/14`)
- Census GEOID: `4813050`

## Certified May 2, 2026 result

| Rank | Candidate | Dallas | Denton | Total | Share | Result |
|---:|---|---:|---:|---:|---:|---|
| 1 | Carolyn Benavides | 3,186 | 1,435 | 4,621 | 27.72% | Elected |
| 2 | Cinthya Noda | 3,426 | 831 | 4,257 | 25.53% | Elected |
| 3 | Dave Jimenez | 3,109 | 1,080 | 4,189 | 25.13% | Not elected |
| 4 | Luis Palomo | 2,505 | 1,100 | 3,605 | 21.62% | Not elected |

The certified order declares Benavides and Noda elected to three-year terms. All four candidate rows remain part of the election evidence.

## Stable identifiers

```text
record_id:   TX:school_district:carrollton-farmers-branch-isd:at_large:DISTRICTWIDE
geometry_id: carrollton-farmers-branch-isd-districtwide
```

## Verified parity

| Layer | Verified count |
|---|---:|
| Candidate/result evidence rows | 4 |
| Seats filled | 2 |
| Official source records | 5 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

- `qa_status = approved`
- `parity_ok = TRUE`
- 25 automated tests passed.
- Permanent read-only CI compares the committed raw snapshot, committed canonical feature, and a fresh Census fetch.
- CFBISD workflow run #7 and repository workflow run #214 passed on the permanent validation configuration.

## Source and QA rules

1. Preserve all four candidates, county subtotals, totals, percentages, and certified ranking.
2. Preserve cumulative voting as the election method, not merely as an explanatory note.
3. Preserve the two-seat cutoff and the two unsuccessful candidates.
4. Do not create separate trustee polygons; trustees are elected districtwide and do not represent geographic areas.
5. Resolve exactly one current Census unified-school-district feature whose official name matches Carrollton-Farmers Branch ISD.
6. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
7. The canonical feature carries `geometry_id = carrollton-farmers-branch-isd-districtwide` and its matching `record_id`.
8. Current-source drift fails CI when geometry, GEOID, stable source attributes, or the canonical join changes.

## Release result

The bounded release is complete in the repository. It preserves the certified cumulative-voting result, raw Census geometry, one approved normalized record, one canonical feature, and permanent live-source drift validation. The Jurisdiction Portfolio is updated only after the pull request merges.
