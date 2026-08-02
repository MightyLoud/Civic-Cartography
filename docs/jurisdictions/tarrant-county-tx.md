# Tarrant County, Texas — Commissioners Court

## Status

Release candidate pending final Tarrant County and repository-wide validation.

## Purpose

Tarrant County tests the county template against a geometry-only source hierarchy with two simultaneous conflicts. The current officeholder roster must be maintained separately from GIS, and the county publishes multiple official Commissioner precinct layers that do not agree. The release therefore uses the layer explicitly labeled effective June 3, 2025 while preserving an undated divergent layer, an explicit 2010 service, and a stale former-commissioner page as non-controlling evidence.

## Jurisdiction identity

- Official name: Tarrant County
- State: Texas
- Jurisdiction type: county
- County FIPS: `439`
- Census GEOID: `48439`
- Representation model: one County Judge elected countywide plus four Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Controlling precinct geometry source: Tarrant County Elections `BondProject/BondProjects/MapServer/3`
- Controlling layer description: Commissioner precinct boundaries effective beginning June 3, 2025
- Stable precinct field: `District_N`
- Stable precinct values: `1`, `2`, `3`, `4`
- Geometry-only source: no officeholder field is used or inferred

## Current official scope

| Office | Representative geography | Officeholder |
|---|---|---|
| County Judge | Countywide | Tim O’Hare |
| Commissioner Precinct 1 | Precinct 1 | Roderick Miles Jr. |
| Commissioner Precinct 2 | Precinct 2 | Alisa Simmons |
| Commissioner Precinct 3 | Precinct 3 | Matt Krause |
| Commissioner Precinct 4 | Precinct 4 | Manny Ramirez |

The current Commissioners Court page and elected-official directory control the roster. Individual official pages independently identify all five officeholders.

## Geometry source hierarchy

### Controlling current layer

`https://mapit.tarrantcounty.com/arcgis/rest/services/BondProject/BondProjects/MapServer/3`

This official Elections-backed layer states that its Commissioner precinct boundaries are effective beginning June 3, 2025. It exposes four polygons with stable `District_N` values 1 through 4 and supports direct GeoJSON. The committed raw and canonical precinct snapshots come from this layer.

### Undated divergent general layer

`https://mapit.tarrantcounty.com/arcgis/rest/services/Dynamic/CommissionerPrecinct/MapServer/0`

This official general-purpose layer also exposes four `District_N` polygons, but every district geometry differs from the explicitly dated June 3, 2025 layer. It is retained as lagging geometry evidence and does not control the release.

### Explicit 2010 service

`https://mapit.tarrantcounty.com/arcgis/rest/services/Dynamic/CommPct_Outline/MapServer`

This still-live official service explicitly describes all 2010 Tarrant County Commissioner precinct boundaries. It is preserved as stale geometry evidence and must never replace the controlling 2025 layer.

## Stale roster handling

The still-live county page at `https://www.tarrantcountytx.gov/en/county-judge/for-redirect-purpose/Maps.html` lists Roy C. Brooks for Precinct 1 and Gary Fickes for Precinct 3. Current official pages identify Roderick Miles Jr. and Matt Krause. The old page is preserved in the source manifest as stale roster evidence and does not control current officeholder values.

## Source contract

1. The controlling June 3, 2025 layer must remain available and return exactly four polygon features.
2. `District_N` must resolve to values `1`, `2`, `3`, and `4`.
3. Direct GeoJSON regeneration from the controlling layer must match the committed raw and canonical snapshots.
4. The undated general layer must remain separately documented; if it converges with or replaces the controlling layer, the source hierarchy must be reviewed.
5. The explicit 2010 service must remain documented but never control current geometry.
6. Current officeholders must come from current official roster and individual pages, not GIS.
7. The County Judge must join only to the Census county feature.
8. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:tarrant:countywide:COUNTYWIDE       -> tarrant-county-countywide
TX:county:tarrant:commissioner_precinct:1    -> tarrant-county-commissioner-precinct-1
TX:county:tarrant:commissioner_precinct:2    -> tarrant-county-commissioner-precinct-2
TX:county:tarrant:commissioner_precinct:3    -> tarrant-county-commissioner-precinct-3
TX:county:tarrant:commissioner_precinct:4    -> tarrant-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 13 |
| Scoped offices | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Current roster: `data/raw/tarrant-county/current-commissioners-court.csv`
- Source manifest: `data/raw/tarrant-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/tarrant-county/tigerweb-county-48439.geojson`
- Raw Commissioner precinct snapshot: `data/raw/tarrant-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/tarrant_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/tarrant_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/tarrant_county_commissioner_precincts.geojson`
- Regression test: `tests/test_tarrant_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-tarrant-county.yml`

## Result

Tarrant County contains five scoped elected offices represented by five geometries: one countywide Census feature and four precinct polygons from the official layer effective June 3, 2025. The release separates officeholders from geometry and preserves three conflicting official sources without allowing any of them to weaken the current roster or boundary model.
