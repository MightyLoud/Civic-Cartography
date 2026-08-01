# Arlington, Texas — Single-Member District Release

## Status

Expanded release validated in GitHub Actions run #97. Arlington now covers all five single-member City Council districts: 1, 2, 3, 4, and 5. Mayor and at-large Districts 6, 7, and 8 remain outside this release.

## Purpose

Arlington proves the Civic Cartography pipeline can preserve and validate multiple official district polygons, current officeholder evidence, election evidence, and one-to-one district joins without replacing previously released artifacts.

## Jurisdiction identity

- Official name: City of Arlington
- State: Texas
- Place FIPS: `04000`
- Census GEOID: `4804000`
- Jurisdiction type: municipality
- District geometry source: City of Arlington OpenData Political Boundary service
- ArcGIS layer: City Council District (`MapServer/0`)
- Stable source district field: `DISTRICTID`
- Released election model: single-member districts

## Released district context

| District | Current official representative | Evidence context |
|---|---|---|
| 1 | Mauricio Galante | Current City profile; first elected May 2024 |
| 2 | Raul H. Gonzalez | Current City profile; first elected November 2020 |
| 3 | Nikkie Hunter | Winner in the bounded May 2, 2026 election evidence |
| 4 | Tom Ware | Winner in the bounded May 2, 2026 election evidence |
| 5 | Brittney Garcia-Dumas | Winner in the bounded May 2, 2026 election evidence |

## Released identifiers

```text
TX:municipality:arlington:district:1  -> arlington-district-1
TX:municipality:arlington:district:2  -> arlington-district-2
TX:municipality:arlington:district:3  -> arlington-district-3
TX:municipality:arlington:district:4  -> arlington-district-4
TX:municipality:arlington:district:5  -> arlington-district-5
```

## Completed parity

| Layer | Count |
|---|---:|
| Current officeholder evidence rows for Districts 1–2 | 2 |
| 2026 candidate evidence rows for Districts 3–5 | 7 |
| Normalized single-member district rows | 5 |
| Canonical GeoJSON features | 5 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records have `qa_status = approved` and `parity_ok = TRUE`.

## Release files

### Districts 1–2

- Officeholder evidence: `data/raw/arlington/current-district-1-2-officeholders.csv`
- Raw official geometry: `data/raw/arlington/city-council-districts-1-2.geojson`
- Normalized records: `data/normalized/arlington_current_districts_1_2.csv`
- Canonical geometry: `data/geojson/arlington_districts_1_2.geojson`

### Districts 3–5

- Candidate evidence: `data/raw/arlington/2026-district-candidates.csv`
- Raw official geometry: `data/raw/arlington/city-council-districts-3-4-5.geojson`
- Normalized records: `data/normalized/arlington_2026_districts.csv`
- Canonical geometry: `data/geojson/arlington_districts_3_4_5.geojson`

### Shared

- Source manifest: `data/raw/arlington/source-manifest.csv`

## Source and QA rules

1. Use only official City of Arlington district geometry from the ArcGIS service.
2. Preserve Districts 1–2 separately from the already released Districts 3–5 artifacts.
3. Keep raw ArcGIS responses separate from canonical map-ready GeoJSON.
4. Canonical features carry unique `geometry_id` and matching `record_id` values.
5. District identifiers resolve unambiguously through `DISTRICTID`.
6. CI regenerates both official district subsets and fails on geometry, stable source-attribute, district-ID, or canonical-join drift.
7. Current officeholder claims use official City profiles; 2026 contest claims use the official City election-results source.
8. Mayor and at-large Districts 6, 7, and 8 remain outside this release.

## Result

Arlington now provides complete single-member district coverage while preserving source lineage by evidence type and maintaining permanent read-only official-source validation.
