# Arlington, Texas — District Geometry Proof

## Status

Released. The bounded Districts 3, 4, and 5 pipeline passed permanent read-only CI in GitHub Actions run #84.

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
- Stable source district field: `DISTRICTID`
- Election model in scope: single-member districts

## 2026 bounded election context

| District | Candidates | Elected representative |
|---|---:|---|
| 3 | 2 | Nikkie Hunter |
| 4 | 3 | Tom Ware |
| 5 | 2 | Brittney Garcia-Dumas |

Seven candidate rows are preserved under `data/raw/arlington/2026-district-candidates.csv`.

## Released identifiers

```text
TX:municipality:arlington:district:3  -> arlington-district-3
TX:municipality:arlington:district:4  -> arlington-district-4
TX:municipality:arlington:district:5  -> arlington-district-5
```

## Completed parity

| Layer | Count |
|---|---:|
| Candidate evidence rows | 7 |
| Normalized district rows | 3 |
| Canonical GeoJSON features | 3 |
| Missing joins | 0 |
| Extra joins | 0 |

All three normalized records have `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Candidate evidence: `data/raw/arlington/2026-district-candidates.csv`
- Source manifest: `data/raw/arlington/source-manifest.csv`
- Raw official geometry: `data/raw/arlington/city-council-districts-3-4-5.geojson`
- Normalized records: `data/normalized/arlington_2026_districts.csv`
- Canonical geometry: `data/geojson/arlington_districts_3_4_5.geojson`

## Source and QA rules

1. Use only official City of Arlington district geometry from the ArcGIS service.
2. Query and preserve Districts 3, 4, and 5 exactly; do not simplify them into approximate shapes.
3. Keep the raw ArcGIS response separate from canonical map-ready GeoJSON.
4. Canonical features carry unique `geometry_id` and matching `record_id` values.
5. District identifiers resolve unambiguously to `3`, `4`, and `5` through `DISTRICTID`.
6. CI regenerates the official features and fails on geometry, stable source-attribute, district-ID, or canonical-join drift.
7. Mayor and at-large Districts 6, 7, and 8 remain outside this bounded release.

## Result

Arlington proves the existing Civic Cartography pattern can move from one-feature at-large municipalities to a multi-feature district layer without weakening raw evidence, QA, parity, or source-drift controls.
