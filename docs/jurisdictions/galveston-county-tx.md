# Galveston County, Texas — Effective-Date Cutover and Abolished Treasurer Office

## Status

Release candidate pending permanent Galveston County and repository-wide validation.

## Purpose

Galveston County tests two source-transition rules in one complete county release:

1. a Commissioner and Justice of the Peace precinct map that became effective June 29, 2026 and supersedes older official-looking GIS services; and
2. a County Treasurer office constitutionally abolished effective January 1, 2024, with treasury functions now published as a division of the County Clerk rather than as a vacancy.

The bounded release contains nine current elected offices represented by five geographies.

## Jurisdiction identity

- Official name: Galveston County
- State: Texas
- Jurisdiction type: county
- County FIPS: `167`
- Census GEOID: `48167`
- Representation model: one County Judge elected countywide, four Commissioners elected from precincts, and four additional countywide constitutional officers
- Current elected offices in scope: 9
- Abolished constitutional offices preserved as structural evidence: 1
- Public ArcGIS Experience item: `e0b0fef416cd42ad991b8ae95d22bb59`
- Experience title: `Galveston Final2`
- Experience owner: `sigler_n`
- Map effective date: June 29, 2026
- Controlling Commissioner layer: `https://services5.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Galveston_County_Commissioner_Precincts_2026/FeatureServer/0`
- Stable precinct field: `Commission`
- Stable precinct values: `1`, `2`, `3`, `4`
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)

## Current elected scope

| Office | Representative geography | Current holder |
|---|---|---|
| County Judge | Countywide | Mark A. Henry |
| County Commissioner Precinct 1 | Precinct 1 | Darrell Apffel |
| County Commissioner Precinct 2 | Precinct 2 | Joe Giusti |
| County Commissioner Precinct 3 | Precinct 3 | Hank Dugie |
| County Commissioner Precinct 4 | Precinct 4 | Dr. Robin Armstrong |
| Sheriff | Countywide | Jimmy Fullen |
| County Clerk | Countywide | Dwight D. Sullivan |
| District Clerk | Countywide | John D. Kinard |
| Tax Assessor-Collector | Countywide | Cheryl E. Johnson |

All nine holders are current elected incumbents.

## Abolished County Treasurer office

The Texas Constitution and enrolled H.J.R. 134 abolish the Galveston County Treasurer office effective January 1, 2024. The current county website publishes `Treasury, a division of the County Clerk`.

The release therefore records:

| Field | Value |
|---|---|
| Office | County Treasurer |
| Status | Abolished |
| Effective date | January 1, 2024 |
| Current officeholder | None |
| Vacancy status | Not applicable |
| Current function destination | Treasury division of the County Clerk |

An official staff directory still associates Commissioner Hank Dugie with a `Treasurer's Office` department tag. That tag is stale historical metadata. His current Commissioner page, the Constitution, H.J.R. 134, and the current Treasury division page supersede it. The release does not create a Treasurer vacancy, incumbent, elected-office row, or geometry.

## June 29, 2026 geometry cutover

The county announced a new Commissioner and Justice of the Peace precinct map effective June 29, 2026. The public map entrypoint is Experience item `e0b0fef416cd42ad991b8ae95d22bb59`.

Portal resolution identified the dedicated post-cutover service:

`Galveston_County_Commissioner_Precincts_2026/FeatureServer/0`

It supplies:

- polygon geometry
- stable field `Commission`
- exactly four values: 1, 2, 3, and 4
- item or layer evidence after the June 29 effective date
- linkage through the controlling public Experience graph

Older generic Commissioner services are retained in the source contract as rejected candidates. At least one must remain demonstrably pre-cutover. The release does not choose a source merely because it is official, public, or contains four precinct polygons; the effective-date and Experience-linkage contract controls selection.

## Source hierarchy

1. Current county office pages and the elected-officials directory control the nine-person roster.
2. The Texas Constitution and H.J.R. 134 control abolition and the January 1, 2024 effective date.
3. The current Treasury page controls the destination of former Treasurer functions.
4. The county's June 29, 2026 announcement controls the map cutover date.
5. Experience item `e0b0fef416cd42ad991b8ae95d22bb59` controls the public map entrypoint.
6. The dedicated 2026 ArcGIS layer controls Commissioner geometry and field `Commission`.
7. Census TIGERweb controls the countywide boundary.
8. Stale or pre-cutover official sources are preserved as conflict evidence but do not control current records.

## Source contract

1. The elected-officials directory and office pages must continue identifying all nine current holders.
2. Commissioners Court pages must identify the County Judge and four Commissioners.
3. The Constitution must continue stating that the Galveston County Treasurer office is abolished.
4. H.J.R. 134 must preserve the January 1, 2024 effective date.
5. The county must continue publishing Treasury as a division of the County Clerk, or an explicitly reviewed successor structure must be approved.
6. No County Treasurer may appear in the current-officeholder or normalized datasets while the abolition remains in force.
7. The county announcement must preserve the June 29, 2026 map effective date.
8. Experience item `e0b0fef416cd42ad991b8ae95d22bb59` must remain titled `Galveston Final2` and owned by `sigler_n`, or an explicitly reviewed replacement must be approved.
9. The controlling service must remain `Galveston_County_Commissioner_Precincts_2026/FeatureServer/0` with polygon geometry, field `Commission`, and values 1 through 4.
10. The controlling service must remain linked through the public Experience graph and retain post-cutover item or layer evidence.
11. At least one older official candidate must remain classified as pre-cutover evidence.
12. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
13. Five countywide offices must share only the Census county feature.
14. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:galveston:countywide:COUNTYWIDE       -> galveston-county-countywide
TX:county:galveston:commissioner_precinct:1    -> galveston-county-commissioner-precinct-1
TX:county:galveston:commissioner_precinct:2    -> galveston-county-commissioner-precinct-2
TX:county:galveston:commissioner_precinct:3    -> galveston-county-commissioner-precinct-3
TX:county:galveston:commissioner_precinct:4    -> galveston-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 9 |
| Official source records | 18 |
| Scoped current elected offices | 9 |
| Current elected holders | 9 |
| Unique current officeholders | 9 |
| Abolished constitutional offices | 1 |
| Vacancies created for abolished office | 0 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

The source-resolution bootstrap proved that the public Experience graph resolves the current Commissioner geometry to `Galveston_County_Commissioner_Precincts_2026/FeatureServer/0` using field `Commission`. Final exact-head workflow evidence is pending.

## Release files

- Current elected roster: `data/raw/galveston-county/current-elected-offices.csv`
- Abolished office evidence: `data/raw/galveston-county/abolished-constitutional-offices.csv`
- Source manifest: `data/raw/galveston-county/source-manifest.csv`
- Reviewed ArcGIS source contract: `data/raw/galveston-county/portal-source-contract.json`
- Raw Census county snapshot: `data/raw/galveston-county/tigerweb-county-48167.geojson`
- Raw Commissioner precinct snapshot: `data/raw/galveston-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/galveston_county_elected_offices.csv`
- Canonical county geometry: `data/geojson/galveston_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/galveston_county_commissioner_precincts.geojson`
- Regression test: `tests/test_galveston_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-galveston-county.yml`

## Result

Galveston County contains nine current elected offices represented by five geometries, plus one abolished constitutional office preserved outside the current roster. The proof demonstrates effective-date source precedence and abolished-office modeling without creating a false vacancy or accepting stale geometry.
