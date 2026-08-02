# Bexar County, Texas — Commissioners Court

## Status

Verified release candidate. Bexar County workflow run #4 and repository workflow run #516 passed; final merge and Jurisdiction Portfolio update remain.

## Purpose

Bexar County tests the county template against a dedicated county MapServer that directly exposes district identity, current Commissioner names, office websites, and GeoJSON geometry. It contrasts with the Travis County hybrid transport model and preserves a separate obsolete official roster as source-conflict evidence.

## Jurisdiction identity

- Official name: Bexar County
- State: Texas
- Jurisdiction type: county
- County FIPS: `029`
- Census GEOID: `48029`
- Representation model: one County Judge elected countywide plus four Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Bexar County GIS `CommissionerPrecincts/MapServer/0`
- Stable precinct field: `Comm`
- Live Commissioner field: `ComName`
- Source website field: `Website`
- Stable precinct values: `1`, `2`, `3`, `4`

## Current official scope

| Office | Representative geography | Officeholder | GIS value |
|---|---|---|---|
| County Judge | Countywide | Peter Sakai | Not applicable |
| Commissioner Precinct 1 | Precinct 1 | Rebeca Clay-Flores | Rebeca Clay-Flores |
| Commissioner Precinct 2 | Precinct 2 | Justin Rodriguez | Justin Rodriguez |
| Commissioner Precinct 3 | Precinct 3 | Grant Moody | Grant Moody |
| Commissioner Precinct 4 | Precinct 4 | Tommy Calvert | Tommy Calvert Jr. |

The Precinct 4 suffix variation is treated as a compatible naming alias. The website roster, individual office page, GIS website URL, and represented precinct all identify the same officeholder.

## Obsolete official roster

A still-live Bexar County elections-finance page lists Nelson W. Wolff as County Judge and Sergio "Chico" Rodriguez, Paul Elizondo, Kevin Wolff, and Tommy Adkisson as Commissioners. That page is retained in the source manifest as an obsolete historical roster and does not control any current officeholder field.

## GIS source contract

1. The official layer must remain available at `https://maps.bexar.org/arcgis/rest/services/CommissionerPrecincts/MapServer/0`.
2. The layer must return exactly four polygon features with `Comm` values `1` through `4`.
3. `ComName` must resolve to Rebeca Clay-Flores, Justin Rodriguez, Grant Moody, and Tommy Calvert Jr.
4. `Website` must resolve to the four official Commissioner office URLs.
5. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
6. The County Judge must join only to the Census county feature.
7. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:bexar:countywide:COUNTYWIDE       -> bexar-county-countywide
TX:county:bexar:commissioner_precinct:1    -> bexar-county-commissioner-precinct-1
TX:county:bexar:commissioner_precinct:2    -> bexar-county-commissioner-precinct-2
TX:county:bexar:commissioner_precinct:3    -> bexar-county-commissioner-precinct-3
TX:county:bexar:commissioner_precinct:4    -> bexar-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 11 |
| Scoped offices | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Bexar County workflow run #4: success
- Repository workflow run #516: success
- Automated tests: 48 passed
- Normalized datasets validated: 17 files
- Current Census snapshot comparison: passed
- Current Bexar County GIS snapshot comparison: passed
- Live `Comm`, `ComName`, and `Website` contract: passed
- Geometry joins: passed
- Combined canonical SHA-256: `a41cb19220f74771bb373e6babeff0d4f8396074b02fcdaf7fe40836c1485216`

## Release files

- Current roster: `data/raw/bexar-county/current-commissioners-court.csv`
- Source manifest: `data/raw/bexar-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/bexar-county/tigerweb-county-48029.geojson`
- Raw Commissioner precinct snapshot: `data/raw/bexar-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/bexar_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/bexar_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/bexar_county_commissioner_precincts.geojson`
- Regression test: `tests/test_bexar_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-bexar-county.yml`

## Result

Bexar County contains five scoped elected offices represented by five verified geometries: one countywide Census feature for the County Judge and four official Commissioner precinct polygons. The dedicated MapServer provides a clean direct-query transfer proof, while the obsolete official finance roster remains explicit QA evidence.
