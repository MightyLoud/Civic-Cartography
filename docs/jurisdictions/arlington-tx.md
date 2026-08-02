# Arlington, Texas — Mixed At-Large and District Structure Release

## Status

Completed mixed-structure release validated in the permanent read-only Arlington workflow run #7 and repository workflow run #229. Arlington now covers the Mayor and all eight City Council districts through five single-member district geometries plus one shared citywide geometry.

## Purpose

Arlington proves one jurisdiction can contain both geographic single-member districts and citywide elected offices without duplicating or inventing boundaries. Five district polygons serve Districts 1–5, while one incorporated-place polygon serves the Mayor and At-Large Districts 6, 7, and 8.

## Jurisdiction identity

- Official name: City of Arlington
- State: Texas
- Place FIPS: `04000`
- Census GEOID: `4804000`
- Jurisdiction type: municipality
- District geometry source: City of Arlington OpenData Political Boundary service
- District ArcGIS layer: City Council District (`MapServer/0`)
- Stable district source field: `DISTRICTID`
- Citywide geometry source: U.S. Census Bureau TIGERweb Current Incorporated Places (`MapServer/28`)

## Representation model

### Single-member districts

| District | Current official representative | Evidence context |
|---|---|---|
| 1 | Mauricio Galante | Current City profile; first elected May 2024 |
| 2 | Raul H. Gonzalez | Current City profile; first elected November 2020 |
| 3 | Nikkie Hunter | Winner in the bounded May 2, 2026 election evidence |
| 4 | Tom Ware | Winner in the bounded May 2, 2026 election evidence |
| 5 | Brittney Garcia-Dumas | Winner in the bounded May 2, 2026 election evidence |

### Citywide offices

| Office | Current official officeholder | Evidence context |
|---|---|---|
| Mayor | Jim Ross | Represents the City at large; re-elected May 2026 |
| Council At-Large District 6 | Long Pham | First elected June 2022; represents the entire city |
| Council At-Large District 7 | Bowie Hogg | First elected May 2022; represents the entire city |
| Council At-Large District 8 | Jason Shelton | Elected in the June 13, 2026 runoff; represents the entire city |

## Stable identifiers

```text
TX:municipality:arlington:district:1  -> arlington-district-1
TX:municipality:arlington:district:2  -> arlington-district-2
TX:municipality:arlington:district:3  -> arlington-district-3
TX:municipality:arlington:district:4  -> arlington-district-4
TX:municipality:arlington:district:5  -> arlington-district-5
TX:municipality:arlington:at_large:CITYWIDE -> arlington-citywide
```

## Completed parity

| Layer | Count |
|---|---:|
| Current citywide officeholder evidence rows | 4 |
| Existing single-member normalized rows | 5 |
| Citywide normalized rows | 1 |
| Total Arlington normalized geography rows | 6 |
| Existing district GeoJSON features | 5 |
| Citywide GeoJSON features | 1 |
| Total Arlington canonical features | 6 |
| Scoped elected offices | 9 |
| Missing joins | 0 |
| Extra joins | 0 |

All six normalized records have `qa_status = approved` and `parity_ok = TRUE`.

## Release files

### District geometry

- `data/raw/arlington/city-council-districts-1-2.geojson`
- `data/raw/arlington/city-council-districts-3-4-5.geojson`
- `data/normalized/arlington_current_districts_1_2.csv`
- `data/normalized/arlington_2026_districts.csv`
- `data/geojson/arlington_districts_1_2.geojson`
- `data/geojson/arlington_districts_3_4_5.geojson`

### Citywide geometry

- Officeholder evidence: `data/raw/arlington/current-citywide-officeholders.csv`
- Raw city boundary: `data/raw/arlington/tigerweb-incorporated-place-4804000.geojson`
- Normalized record: `data/normalized/arlington_citywide.csv`
- Canonical geometry: `data/geojson/arlington_citywide.geojson`

### Shared

- Source manifest: `data/raw/arlington/source-manifest.csv`

## Source and QA rules

1. Preserve the five released single-member district artifacts unchanged.
2. Model Mayor and At-Large Districts 6, 7, and 8 as four offices sharing one citywide geography.
3. Do not create separate polygons for the at-large office numbers.
4. Keep raw Census and ArcGIS responses separate from canonical map-ready GeoJSON.
5. Canonical features carry unique `geometry_id` and matching `record_id` values.
6. CI regenerates the citywide feature and both district subsets and fails on geometry, GEOID, stable source attributes, district IDs, or canonical-join drift.
7. The Jurisdiction Portfolio must maintain one Arlington row covering all nine offices.

## Result

Arlington is the first completed mixed at-large-and-district jurisdiction: six official geometries serve nine elected offices with complete one-to-one joins and permanent read-only source validation.
