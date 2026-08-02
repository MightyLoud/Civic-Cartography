# Dallas County, Texas — Commissioners Court and Countywide Constitutional Offices

## Status

Verified ten-office release package. First-pass pre-merge validation succeeded in Dallas County workflow run #21 and repository workflow run #810.

## Purpose

Dallas County tests three related civic-data contracts. The county publicly uses `Commissioner District` and `Road & Bridge District`, while redistricting materials also use `commissioner precinct`; the official searchable application carries current commissioner names and links inside the geometry layer; and six countywide elected offices must share one county geometry without creating duplicate normalized rows. The release preserves source terminology, uses an independently maintained roster as the controlling officeholder evidence, and keeps a conflicting pair of official Sheriff swearing-year claims as non-controlling historical evidence.

## Jurisdiction identity

- Official name: Dallas County
- State: Texas
- Jurisdiction type: county
- County FIPS: `113`
- Census GEOID: `48113`
- Representation model: six countywide elected offices plus four Commissioners elected from districts
- Total scoped elected offices: ten
- Current holders selected by election: ten
- Unique current officeholders: ten
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

| Office | Representative geography | Current holder | Current selection status |
|---|---|---|---|
| County Judge | Countywide | Clay Jenkins | Elected |
| Sheriff | Countywide | Marian Brown | Elected |
| County Clerk | Countywide | John F. Warren | Elected |
| District Clerk | Countywide | Felicia Pitre | Elected |
| Tax Assessor/Collector | Countywide | John R. Ames, CTA | Elected |
| County Treasurer | Countywide | Pauline Medrano | Elected |
| Commissioner District 1 | District 1 | Dr. Theresa Daniel | Elected |
| Commissioner District 2 | District 2 | Andy Sommerman | Elected |
| Commissioner District 3 | District 3 | John Wiley Price | Elected |
| Commissioner District 4 | District 4 | Dr. Elba Garcia | Elected |

The elected-official directory defines all ten roles as elected county offices and identifies the same current holders. Individual office pages and independent county cross-checks support each new countywide holder.

## Countywide office handling

Six countywide roles share the single Dallas County Census feature:

- County Judge — Clay Jenkins
- Sheriff — Marian Brown
- County Clerk — John F. Warren
- District Clerk — Felicia Pitre
- Tax Assessor/Collector — John R. Ames, CTA
- County Treasurer — Pauline Medrano

The five newly added offices are separately elected and represented through the existing countywide normalized record. The release does not create additional countywide geometries or duplicate normalized rows.

Each new office has current official evidence and an independent official cross-check:

- The Sheriff homepage and executive-team page identify Marian Brown.
- The elected-official directory and County Clerk payment instructions identify John F. Warren.
- The elected-official directory and District Clerk biography identify Felicia Pitre.
- The Tax Assessor/Collector biography and current 2026 Auditor reports identify John R. Ames, CTA.
- The Treasurer biography and current 2026 Auditor reports identify Pauline Medrano.

## Sheriff historical-date conflict

Dallas County's official Sheriff pages agree that Marian Brown is the current Sheriff but disagree on the initial swearing year:

- The current executive-team page says she was sworn in on January 1, 2019.
- The official Sheriff biography says she was sworn in on January 1, 2018.

The release preserves both claims as divergent historical evidence. The conflict does not alter the current officeholder record because the current Sheriff homepage and elected-official directory independently identify Marian Brown.

## Nomenclature handling

Dallas County uses three related labels for the same four elected geographies:

- `Commissioner District` on the current roster and map interface
- `Road & Bridge District` on Commissioner office pages and administrative material
- `commissioner precinct` in redistricting criteria and adopted-map material

The source-facing `district_name` and office names preserve `Commissioner District`. The canonical `district_type` remains `commissioner_precinct`, matching the repository's Texas county model. This is a vocabulary normalization, not a change in office structure or geometry.

## Official application and layer resolution

The county's official `Who is My Commissioner?` page links to a Dallas County GIS ArcGIS application:

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

The official redistricting page publishes the adopted post-2020-Census Commissioners Court map and describes the redistricting criteria using commissioner-precinct terminology. The District 1 biography separately states that the newly drawn district was voted on in 2021. The controlling layer's title identifies it as the Dallas County adopted 2021 Commissioners Court plan.

## Source contract

1. The official county page must continue to link the searchable application ID `929bdc6b485f47428f2e26266bd3ed81`.
2. The application must continue to resolve web map ID `a9d7fe8a050848ed9d5f08086436ed3f`.
3. The web map must continue to reference the adopted 2021 Commissioners Court layer.
4. The layer must remain polygon geometry with fields `DISTRICT`, `Name`, `Comm_URL`, and `Photo`.
5. `DISTRICT` must resolve to exactly 1 through 4.
6. Live `Name`, `Comm_URL`, and `Photo` values must match the current four-Commissioner contract.
7. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
8. Dallas's public District terminology must remain explicit while canonical `district_type` stays `commissioner_precinct`.
9. The elected-official directory and current office pages must identify all ten scoped offices and current holders.
10. The Sheriff 2018/2019 conflict must remain explicit until controlling official sources converge.
11. The six countywide offices must share the existing Census feature.
12. Every normalized row must join exactly one canonical feature.

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
| Current-officeholder evidence rows | 10 |
| Official source records | 23 |
| Scoped elected offices | 10 |
| Current holders selected by election | 10 |
| Unique current officeholders | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-district features | 4 |
| Geometry changes | 0 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Dallas County workflow run #21: success
- Repository workflow run #810: success
- Automated tests: 66 passed
- Normalized datasets validated: 21 files
- Application item, web map, operational layer, and live roster contract: passed
- Current Commissioner District snapshot comparison: passed
- Current Census snapshot comparison: passed
- Geometry joins: passed
- Combined canonical SHA-256: `1fcefca2f253e3176fb07d15e8a070073100b9f18ae9f030ef5a8a7203c7357c`

## Release files

- Current Commissioners Court roster: `data/raw/dallas-county/current-commissioners-court.csv`
- Current countywide constitutional offices: `data/raw/dallas-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/dallas-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/dallas-county/tigerweb-county-48113.geojson`
- Raw Commissioner District snapshot: `data/raw/dallas-county/commissioner-districts-1-4.geojson`
- Normalized records: `data/normalized/dallas_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/dallas_county_countywide.geojson`
- Canonical Commissioner District geometry: `data/geojson/dallas_county_commissioner_districts.geojson`
- Regression test: `tests/test_dallas_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-dallas-county.yml`

## Result

Dallas County contains ten scoped elected offices represented by five geometries. Six countywide offices share one Census feature. Commissioner Districts 1 through 4 retain the official adopted 2021 polygons, Dallas County's public terminology, and canonical `commissioner_precinct` mapping. The Sheriff 2018/2019 swearing-year conflict remains explicit without controlling the current officeholder field.
