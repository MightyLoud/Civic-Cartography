# Arlington, Texas — District Geometry Proof

## Purpose

Arlington is the first Civic Cartography jurisdiction that requires multiple official district polygons and one-to-one district joins. The bounded scope is the three single-member City Council districts contested in the May 2, 2026 election: Districts 3, 4, and 5.

## Jurisdiction identity

- Official name: City of Arlington
- State: Texas
- Place FIPS: `04000`
- Census GEOID: `4804000`
- Jurisdiction type: municipality
- District geometry source: City of Arlington OpenData Political Boundary service
- ArcGIS layer: City Council District (`MapServer/0`)
- Election model in scope: single-member districts

## 2026 bounded election context

| District | Candidates | Elected representative |
|---|---:|---|
| 3 | 2 | Nikkie Hunter |
| 4 | 3 | Tom Ware |
| 5 | 2 | Brittney Garcia-Dumas |

Seven candidate rows are preserved under `data/raw/arlington/2026-district-candidates.csv`.

## Planned normalized identifiers

```text
TX:municipality:arlington:district:3  -> arlington-district-3
TX:municipality:arlington:district:4  -> arlington-district-4
TX:municipality:arlington:district:5  -> arlington-district-5
```

## Target parity

| Layer | Expected count |
|---|---:|
| Candidate evidence rows | 7 |
| Normalized district rows | 3 |
| Canonical GeoJSON features | 3 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Use only official City of Arlington district geometry from the ArcGIS service.
2. Query and preserve Districts 3, 4, and 5 exactly; do not simplify them into approximate shapes.
3. Keep the raw ArcGIS response separate from canonical map-ready GeoJSON.
4. Canonical features must carry unique `geometry_id` and matching `record_id` values.
5. District identifiers must resolve unambiguously to `3`, `4`, and `5`.
6. Current-source drift must fail CI when district geometry or stable source attributes change.
7. Mayor and at-large Districts 6, 7, and 8 are outside this issue.

## Completion rule

Arlington is not complete until raw candidate evidence exists, raw district geometry exists, three normalized rows exist, three canonical features exist, QA is approved, `parity_ok = TRUE`, CI is green, the pull request is merged, and the Jurisdiction Portfolio reflects the released state.
