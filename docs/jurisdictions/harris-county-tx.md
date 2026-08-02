# Harris County, Texas — Commissioners Court

## Status

Verified release package. Harris County workflow run #4 and repository workflow run #569 completed successfully.

## Purpose

Harris County tests the county template against a current authoritative FeatureServer whose district geometry and roster attributes are maintained together, while the current court roster is independently cross-checked through official county pages. It also tests explicit preservation of a still-live official ArcGIS item that describes the obsolete 2011 precinct boundaries.

## Jurisdiction identity

- Official name: Harris County
- State: Texas
- Jurisdiction type: county
- County FIPS: `201`
- Census GEOID: `48201`
- Representation model: one County Judge elected countywide plus four Commissioners elected from precincts
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Harris County GIS `Commissioner_Precincts/FeatureServer/0`
- Current ArcGIS item: `a51b563da9ad479786a05f5c9f946e4c`
- Stable precinct field: `PCT_NO`
- Live Commissioner field: `COMMISSION`
- Source website field: `URL`
- Stable precinct values: `1`, `2`, `3`, `4`

## Current official scope

| Office | Representative geography | Officeholder | GIS value |
|---|---|---|---|
| County Judge | Countywide | Lina Hidalgo | Not applicable |
| Commissioner Precinct 1 | Precinct 1 | Rodney Ellis | Rodney Ellis |
| Commissioner Precinct 2 | Precinct 2 | Adrian Garcia | Adrian Garcia |
| Commissioner Precinct 3 | Precinct 3 | Tom S. Ramsey | Tom S. Ramsey |
| Commissioner Precinct 4 | Precinct 4 | Lesley Briones | Lesley Briones |

The live `COMMISSION` field agrees with the current official roster for all four precincts.

## Legacy URL and stale geometry handling

The live FeatureServer's Precinct 4 `URL` value remains `https://www.hcp4.net/`, while the current official office site is `https://cp4.harriscountytx.gov/`. The release preserves the GIS value as a legacy URL alias and uses the current official biography as controlling roster evidence.

A separate still-live official ArcGIS item, `44771fa82aef4656a02879effbe52e60`, describes the court-approved 2011 Commissioner precinct boundaries and was last updated in 2019. It is preserved in the source manifest as stale-geometry evidence and does not control the current release. The current authoritative item was updated in July 2026, and its data and schema were updated in May 2026.

## GIS source contract

1. The current FeatureServer must remain available at `https://services.arcgis.com/su8ic9KbA7PYVxPS/ArcGIS/rest/services/Commissioner_Precincts/FeatureServer/0`.
2. The layer must return exactly four polygon features with `PCT_NO` values `1` through `4`.
3. `COMMISSION` must resolve to Rodney Ellis, Adrian Garcia, Tom S. Ramsey, and Lesley Briones.
4. `URL` must resolve to the four committed source values, including the legacy Precinct 4 domain.
5. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
6. The County Judge must join only to the Census county feature.
7. Every normalized row must join exactly one canonical feature.
8. The obsolete 2011 ArcGIS item must remain documented but must never replace the current FeatureServer.

## Stable identifiers

```text
TX:county:harris:countywide:COUNTYWIDE       -> harris-county-countywide
TX:county:harris:commissioner_precinct:1    -> harris-county-commissioner-precinct-1
TX:county:harris:commissioner_precinct:2    -> harris-county-commissioner-precinct-2
TX:county:harris:commissioner_precinct:3    -> harris-county-commissioner-precinct-3
TX:county:harris:commissioner_precinct:4    -> harris-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 5 |
| Official source records | 12 |
| Scoped offices | 5 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Harris County workflow run #4: success
- Repository workflow run #569: success
- Automated tests: 50 passed
- Normalized datasets validated: 18 files
- Current Census snapshot comparison: passed
- Current Harris County FeatureServer snapshot comparison: passed
- Live `PCT_NO`, `COMMISSION`, and `URL` contract: passed
- Geometry joins: passed
- Combined canonical SHA-256: `9d2d53995461f9f1f573858eff696fc92be7542b6623a9513d6b6d1aff690d28`

## Release files

- Current roster: `data/raw/harris-county/current-commissioners-court.csv`
- Source manifest: `data/raw/harris-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/harris-county/tigerweb-county-48201.geojson`
- Raw Commissioner precinct snapshot: `data/raw/harris-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/harris_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/harris_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/harris_county_commissioner_precincts.geojson`
- Regression test: `tests/test_harris_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-harris-county.yml`

## Result

Harris County contains five scoped elected offices represented by five verified geometries: one countywide Census feature for the County Judge and four current official Commissioner precinct polygons. The release treats `PCT_NO` as the stable join field, validates the current `COMMISSION` roster attributes, preserves the Precinct 4 legacy URL, and keeps the obsolete 2011-boundary item explicit as stale-source evidence.
