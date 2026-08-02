# Hidalgo County, Texas — Dual Commissioners Court and Drainage District Board

## Status

Verified release package. First-pass pre-merge validation succeeded in Hidalgo County workflow run #10 and repository workflow run #958.

## Purpose

Hidalgo County tests a complete ten-office county release in which the five elected Commissioners Court members concurrently serve as the Hidalgo County Drainage District No. 1 Board of Directors. The public-body assignment is preserved without creating duplicate elected offices, officeholders, normalized geography rows, or canonical features.

## Jurisdiction identity

- Official name: Hidalgo County
- State: Texas
- Jurisdiction type: county
- County FIPS: `215`
- Census GEOID: `48215`
- Representation model: one County Judge elected countywide, four Commissioners elected from precincts, and five additional countywide constitutional officers
- Official roster authority: Hidalgo County County Officials directory and Commissioners Court pages
- Drainage District body: Hidalgo County Drainage District No. 1
- Drainage District structure: County Judge as Chairman plus four County Commissioners as board members
- Reviewed ArcGIS item ID: `bc95c6e0bbed4ba98a16b303219de88a`
- ArcGIS item title: `Hidalgo County Basemap`
- ArcGIS item owner: `rpresas`
- County-associated operational layer: `https://services9.arcgis.com/dwMDP55HTfoj4n1c/arcgis/rest/services/County_Commissioners_View/FeatureServer/0`
- Stable precinct field: `DISTRICT`
- Stable precinct values: `1`, `2`, `3`, `4`
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)

## Current elected scope

| Office | Representative geography | Current holder |
|---|---|---|
| County Judge | Countywide | Richard F. Cortez |
| County Commissioner Precinct 1 | Precinct 1 | David L. Fuentes |
| County Commissioner Precinct 2 | Precinct 2 | Eduardo “Eddie” Cantu |
| County Commissioner Precinct 3 | Precinct 3 | Everardo “Ever” Villarreal |
| County Commissioner Precinct 4 | Precinct 4 | Ellie Torres |
| Sheriff | Countywide | J.E. “Eddie” Guerra |
| County Clerk | Countywide | Arturo Guajardo, Jr. |
| District Clerk | Countywide | Laura Hinojosa |
| Tax Assessor-Collector | Countywide | Pablo “Paul” Villarreal, Jr. |
| County Treasurer | Countywide | Lita Leo |

All ten holders are current elected incumbents.

## Concurrent Drainage District board

The official Drainage District Board of Directors page identifies the same five Commissioners Court members:

| Drainage District role | Source elected office | Current holder |
|---|---|---|
| Chairman of the Board | County Judge | Richard F. Cortez |
| Board Member | Commissioner Precinct 1 | David L. Fuentes |
| Board Member | Commissioner Precinct 2 | Eduardo “Eddie” Cantu |
| Board Member | Commissioner Precinct 3 | Everardo “Ever” Villarreal |
| Board Member | Commissioner Precinct 4 | Ellie Torres |

The Drainage District administration page states that the board consists of the County Judge and four County Commissioners. Its history states that management and control transferred to Commissioners Court in 1939. The county schedules Commissioners Court and Drainage District No. 1 as separate consecutive public meetings.

The release therefore models five public-body assignments while retaining only ten elected offices and ten officeholder evidence rows.

## Geometry source hierarchy

The official County Officials directory and office pages control the elected roster. The official county maps page supplies Commissioner-precinct map context, not roster authority. The official November 13, 2021 redistricting action controls adoption of the current Commissioner precinct plan.

A reviewed county-associated ArcGIS item titled `Hidalgo County Basemap`, owned by `rpresas`, resolves operational Commissioner polygons to:

`https://services9.arcgis.com/dwMDP55HTfoj4n1c/arcgis/rest/services/County_Commissioners_View/FeatureServer/0`

The layer supplies:

- polygon geometry
- stable field `DISTRICT`
- exactly four values: 1, 2, 3, and 4

The release does not infer officeholders from GIS. Official county pages control names; the reviewed ArcGIS layer controls geometry; the 2021 county action controls plan adoption.

## Source contract

1. The County Officials directory must identify all ten elected holders.
2. Commissioners Court pages must identify the current County Judge and four Commissioners.
3. The Drainage District Board page must identify the same five people and their board roles.
4. The Drainage District administration page must continue defining the board as the County Judge and four Commissioners.
5. The Drainage District history must preserve the 1939 transfer of management and control to Commissioners Court.
6. County meeting pages must preserve separate Commissioners Court and Drainage District meeting identities.
7. The county maps page must preserve Commissioner-precinct map context without being treated as the roster authority.
8. The 2021 county redistricting record must preserve Commissioner precinct adoption evidence.
9. ArcGIS item `bc95c6e0bbed4ba98a16b303219de88a` must remain titled `Hidalgo County Basemap` and owned by `rpresas`, or an explicitly reviewed replacement must be approved.
10. The operational layer must remain polygon geometry with field `DISTRICT` and values 1 through 4.
11. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
12. Six countywide offices must share only the Census county feature.
13. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:hidalgo:countywide:COUNTYWIDE       -> hidalgo-county-countywide
TX:county:hidalgo:commissioner_precinct:1    -> hidalgo-county-commissioner-precinct-1
TX:county:hidalgo:commissioner_precinct:2    -> hidalgo-county-commissioner-precinct-2
TX:county:hidalgo:commissioner_precinct:3    -> hidalgo-county-commissioner-precinct-3
TX:county:hidalgo:commissioner_precinct:4    -> hidalgo-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 10 |
| Official source records | 20 |
| Scoped elected offices | 10 |
| Current elected holders | 10 |
| Unique current officeholders | 10 |
| Drainage District board assignments | 5 |
| Duplicate elected offices created for board service | 0 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Source-resolution bootstrap: ArcGIS item `bc95c6e0bbed4ba98a16b303219de88a` resolves to `County_Commissioners_View/FeatureServer/0` using field `DISTRICT`
- Hidalgo County workflow run #10: success
- Repository workflow run #958: success
- Automated tests: 76 passed
- Normalized datasets validated: 24 files
- Ten-office roster validation: passed
- Five-person Commissioners Court / Drainage District board overlap: passed
- Separate public-body meeting identity: passed
- 2021 redistricting evidence: passed
- Current Commissioner precinct snapshot comparison: passed
- Current Census snapshot comparison: passed
- Geometry joins: passed
- Combined canonical SHA-256: `ce2e958d1febb028d57089dc6a6c458f39d188d981c368622d33d86881f852a2`

## Release files

- Current elected roster: `data/raw/hidalgo-county/current-elected-offices.csv`
- Concurrent board assignments: `data/raw/hidalgo-county/current-drainage-district-board.csv`
- Source manifest: `data/raw/hidalgo-county/source-manifest.csv`
- Reviewed ArcGIS source contract: `data/raw/hidalgo-county/portal-source-contract.json`
- Raw Census county snapshot: `data/raw/hidalgo-county/tigerweb-county-48215.geojson`
- Raw Commissioner precinct snapshot: `data/raw/hidalgo-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/hidalgo_county_elected_offices.csv`
- Canonical county geometry: `data/geojson/hidalgo_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/hidalgo_county_commissioner_precincts.geojson`
- Regression test: `tests/test_hidalgo_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-hidalgo-county.yml`

## Result

Hidalgo County contains ten scoped elected offices represented by five geometries, plus five concurrent Drainage District board assignments derived from the County Judge and four Commissioner offices. The proof demonstrates a dual-public-body relationship without duplicating elected offices, people, or geography.
