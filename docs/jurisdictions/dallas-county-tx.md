# Dallas County, Texas — Commissioners Court

## Status

Release candidate pending Dallas County and repository-wide validation.

## Purpose

Dallas County tests nomenclature normalization and roster-bearing GIS. The county publicly uses `Commissioner District` and `Road & Bridge District`, while its redistricting materials also use `commissioner precinct`. The release preserves those source terms while normalizing the four geographic seats to the repository’s canonical `commissioner_precinct` type. The official searchable application also carries current commissioner names and links inside the geometry layer, but the independently maintained county roster remains the controlling officeholder evidence.

## Jurisdiction identity

- Official name: Dallas County
- State: Texas
- Jurisdiction type: county
- County FIPS: `113`
- Census GEOID: `48113`
- Representation model: one County Judge elected countywide plus four Commissioners elected from districts
- Public geography terms: Commissioner District and Road & Bridge District
- Redistricting term: commissioner precinct
- Canonical geography type: `commissioner_precinct`
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Official searchable application: `929bdc6b485f47428f2e26266bd3ed81`
- Official web map: `a9d7fe8a050848ed9d5f08086436ed3f`
- Controlling district layer: Dallas County GIS `DC_CCs_Adopted_2021_Rev1/FeatureServer/0`
- Stable district field: `DISTRICT`
- Stable district values: `1`, `2`, `3`, `4`
- Live roster fields: `Name`, `Comm_URL`, and `Photo`

## Current official scope

| Office | Representative geography | Current holder |
|---|---|---|
| County Judge | Countywide | Clay Jenkins |
| Commissioner District 1 | District 1 | Dr. Theresa Daniel |
| Commissioner District 2 | District 2 | Andy Sommerman |
| Commissioner District 3 | District 3 | John Wiley Price |
| Commissioner District 4 | District 4 | Dr. Elba Garcia |

The county government overview defines four districts whose voters elect Commissioners and one countywide Judge elected by all county voters. The `Who is My Commissioner?` page and elected-official directory independently list the same five current holders.

## Nomenclature handling

Dallas County uses three related labels for the same four elected geographies:

- `Commissioner District` on the current roster and map interface
- `Road & Bridge District` on Commissioner office pages and administrative material
- `commissioner precinct` in redistricting criteria and adopted-map material

The source-facing `district_name` and office names preserve `Commissioner District`. The canonical `district_type` remains `commissioner_precinct`, matching the repository’s Texas county model. This is a vocabulary normalization, not a change in office structure or geometry.

## Official application and layer resolution

The county’s official `Who is My Commissioner?` page links to a Dallas County GIS ArcGIS application:

`https://dallascountygis.maps.arcgis.com/apps/webappviewer/index.html?id=929bdc6b485f47428f2e26266bd3ed81`

The application belongs to ArcGIS organization `zqe2kwz79KUqUvxC` and describes Dallas County as four Commissioner districts plus one countywide Judge. Its configured web map is:

`a9d7fe8a050848ed9d5f08086436ed3f`

That web map references the controlling operational layer:

`https://services3.arcgis.com/zqe2kwz79KUqUvxC/arcgis/rest/services/DC_CCs_Adopted_2021_Rev1/FeatureServer/0`

The layer exposes exactly four polygons with the following live attributes:

| `DISTRICT` | `Name` | `Comm_URL` suffix | `Photo` |
|---:|---|---|---|
| 1 | Dr. Theresa Daniel | `district1/` | `COMM. DIST. 1` |
| 2 | Andy Sommerman | `district2/` | `COMM. DIST. 2` |
| 3 | John Wiley Price | `district3/` | `COMM. DIST. 3` |
| 4 | Dr. Elba Garcia | `district4/` | `COMM. DIST. 4` |

The live names match the independently maintained current roster. The geometry is therefore roster-bearing, but the release does not infer officeholders from polygon labels alone.

## Redistricting evidence

The official redistricting page publishes the adopted post-2020-Census Commissioners Court map and describes the redistricting criteria using commissioner-precinct terminology. The District 1 biography separately states that the newly drawn district was voted on in 2021. The controlling layer’s title identifies it as the Dallas County adopted 2021 Commissioners Court plan.

## Source contract

1. The official county page must continue to link the searchable application ID `929bdc6b485f47428f2e26266bd3ed81`.
2. The application must continue to resolve web map ID `a9d7fe8a050848ed9d5f08086436ed3f`.
3. The web map must continue to reference the adopted 2021 Commissioners Court layer.
4. The layer must remain polygon geometry with fields `DISTRICT`, `Name`, `Comm_URL`, and `Photo`.
5. `DISTRICT` must resolve to exactly 1 through 4.
6. Live `Name`, `Comm_URL`, and `Photo` values must match the current four-Commissioner contract.
7. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
8. Dallas’s public District terminology must remain explicit while canonical `district_type` stays `commissioner_precinct`.
9. The County Judge must join only to the Census county feature.
10. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:dallas:countywide:COUNTYWIDE       -> dallas-county-countywide
TX:county:dallas:commissioner_precinct:1    -> dallas-county-commissioner-district-1
TX:county:dallas:commissioner_precinct:2    -> dallas-county-commissioner-district-2
TX:county:dallas:commissioner_precinct:3    -> dallas-county-commissioner-district-3
TX:county:dallas:commissioner_precinct:4    -> dallas-county-commissioner-district-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 13 |
| Scoped elected offices | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-district features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

Pending final exact-head Dallas County and repository-wide workflow results.

## Release files

- Current roster: `data/raw/dallas-county/current-commissioners-court.csv`
- Source manifest: `data/raw/dallas-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/dallas-county/tigerweb-county-48113.geojson`
- Raw Commissioner District snapshot: `data/raw/dallas-county/commissioner-districts-1-4.geojson`
- Normalized records: `data/normalized/dallas_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/dallas_county_countywide.geojson`
- Canonical Commissioner District geometry: `data/geojson/dallas_county_commissioner_districts.geojson`
- Regression test: `tests/test_dallas_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-dallas-county.yml`

## Result

Dallas County contains five scoped elected offices represented by five geometries. Clay Jenkins joins to one countywide Census feature. Commissioner Districts 1 through 4 join to the official adopted 2021 polygons while preserving Dallas County’s public terminology and canonicalizing the geography type for cross-county interoperability.
