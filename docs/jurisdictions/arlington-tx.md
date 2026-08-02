# Arlington, Texas — Mixed At-Large and District Structure

## Status

Release candidate. Arlington’s five single-member districts are already released. This extension adds the Mayor and At-Large Districts 6, 7, and 8 through one citywide geography without modifying the existing district artifacts.

## Purpose

Arlington is the Civic Cartography proof that one jurisdiction can contain both geographic single-member districts and citywide elected offices. The final model must preserve five district polygons plus one shared citywide polygon serving four at-large offices.

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

## Target parity

| Layer | Expected count |
|---|---:|
| Current citywide officeholder evidence rows | 4 |
| Existing single-member normalized rows | 5 |
| New citywide normalized rows | 1 |
| Total Arlington normalized geography rows | 6 |
| Existing district GeoJSON features | 5 |
| New citywide GeoJSON features | 1 |
| Total Arlington canonical features | 6 |
| Scoped elected offices | 9 |
| Missing joins | 0 |
| Extra joins | 0 |

## Release files

### Existing district geometry

- `data/raw/arlington/city-council-districts-1-2.geojson`
- `data/raw/arlington/city-council-districts-3-4-5.geojson`
- `data/normalized/arlington_current_districts_1_2.csv`
- `data/normalized/arlington_2026_districts.csv`
- `data/geojson/arlington_districts_1_2.geojson`
- `data/geojson/arlington_districts_3_4_5.geojson`

### Mixed-structure extension

- Officeholder evidence: `data/raw/arlington/current-citywide-officeholders.csv`
- Planned raw city boundary: `data/raw/arlington/tigerweb-incorporated-place-4804000.geojson`
- Planned normalized record: `data/normalized/arlington_citywide.csv`
- Planned canonical geometry: `data/geojson/arlington_citywide.geojson`

### Shared

- Source manifest: `data/raw/arlington/source-manifest.csv`

## Source and QA rules

1. Preserve the five released single-member district artifacts unchanged.
2. Model Mayor and At-Large Districts 6, 7, and 8 as four offices sharing one citywide geography.
3. Do not create separate polygons for the at-large office numbers.
4. Keep raw Census and ArcGIS responses separate from canonical map-ready GeoJSON.
5. Canonical features must carry unique `geometry_id` and matching `record_id` values.
6. CI must fail on geometry, GEOID, stable source attributes, district IDs, or canonical-join drift.
7. The final portfolio update must modify the existing Arlington row rather than creating a duplicate jurisdiction.

## Completion rule

Arlington is not complete as a mixed-structure jurisdiction until the four citywide offices, one raw Census feature, one approved normalized citywide record, one canonical citywide feature, six total unique geography joins, green CI, a merged pull request, and the existing Jurisdiction Portfolio row all agree.
