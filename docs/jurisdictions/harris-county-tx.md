# Harris County, Texas — Commissioners Court and Countywide Constitutional Offices

## Status

Verified ten-office release package. Pre-merge validation succeeded in Harris County workflow run #32 and repository workflow run #597.

## Purpose

Harris County first proved the county template against a current authoritative FeatureServer whose district geometry and roster attributes are maintained together. This extension adds five separately elected countywide constitutional offices while preserving the existing one-countywide-plus-four-precinct geometry package and explicitly documenting the Tax Assessor-Collector transition from Ann Harris Bennett to Annette Ramirez.

## Jurisdiction identity

- Official name: Harris County
- State: Texas
- Jurisdiction type: county
- County FIPS: `201`
- Census GEOID: `48201`
- Representation model: six countywide elected offices plus four Commissioners elected from precincts
- Separately elected positions in scope: ten
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Harris County GIS `Commissioner_Precincts/FeatureServer/0`
- Current ArcGIS item: `a51b563da9ad479786a05f5c9f946e4c`
- Stable precinct field: `PCT_NO`
- Live Commissioner field: `COMMISSION`
- Source website field: `URL`
- Stable precinct values: `1`, `2`, `3`, `4`

## Current official scope

| Office | Representative geography | Officeholder | Selection structure |
|---|---|---|---|
| County Judge | Countywide | Lina Hidalgo | Separately elected |
| Sheriff | Countywide | Ed Gonzalez | Separately elected |
| County Clerk | Countywide | Teneshia Hudspeth | Separately elected |
| District Clerk | Countywide | Marilyn Burgess | Separately elected |
| Tax Assessor-Collector | Countywide | Annette Ramirez | Separately elected |
| County Treasurer | Countywide | Carla L. Wyatt | Separately elected |
| Commissioner Precinct 1 | Precinct 1 | Rodney Ellis | Separately elected from precinct |
| Commissioner Precinct 2 | Precinct 2 | Adrian Garcia | Separately elected from precinct |
| Commissioner Precinct 3 | Precinct 3 | Tom S. Ramsey | Separately elected from precinct |
| Commissioner Precinct 4 | Precinct 4 | Lesley Briones | Separately elected from precinct |

All six countywide offices share the single Census county feature. Commissioners Precincts 1 through 4 retain their four current official FeatureServer polygons.

## Tax Assessor-Collector transition

Annette Ramirez was sworn in as Harris County Tax Assessor-Collector on January 1, 2025. The current elected-official directory and current Tax Office pages identify Ramirez.

A still-live Tax Office voter-registration page displays Annette Ramirez in its current header but states in the body that Ann Harris Bennett serves as Tax Assessor-Collector. The release preserves that page as stale embedded-content evidence and does not allow it to override the current officeholder record.

## Legacy URL and stale geometry handling

The live FeatureServer's Precinct 4 `URL` value remains `https://www.hcp4.net/`, while the current official office site is `https://cp4.harriscountytx.gov/`. The release preserves the GIS value as a legacy URL alias and uses the current official biography as controlling roster evidence.

A separate still-live official ArcGIS item, `44771fa82aef4656a02879effbe52e60`, describes the court-approved 2011 Commissioner precinct boundaries and was last updated in 2019. It remains in the source manifest as stale-geometry evidence and does not control the current release.

## GIS source contract

1. The current FeatureServer must remain available at `https://services.arcgis.com/su8ic9KbA7PYVxPS/ArcGIS/rest/services/Commissioner_Precincts/FeatureServer/0`.
2. The layer must return exactly four polygon features with `PCT_NO` values `1` through `4`.
3. `COMMISSION` must resolve to Rodney Ellis, Adrian Garcia, Tom S. Ramsey, and Lesley Briones.
4. `URL` must resolve to the four committed source values, including the legacy Precinct 4 domain.
5. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
6. All six countywide offices must share the single Census county feature.
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
| Current-officeholder evidence rows | 10 |
| Official source records | 20 |
| Scoped elected offices | 10 |
| Unique current officeholders | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Harris County workflow run #32: success
- Repository workflow run #597: success
- Automated tests: 51 passed
- Normalized datasets validated: 18 files
- Current Census snapshot comparison: passed
- Current Harris County FeatureServer snapshot comparison: passed
- Live `PCT_NO`, `COMMISSION`, and `URL` contract: passed
- Geometry joins: passed
- Geometry changes: 0
- Combined canonical SHA-256: `9d2d53995461f9f1f573858eff696fc92be7542b6623a9513d6b6d1aff690d28`

## Release files

- Commissioners Court roster: `data/raw/harris-county/current-commissioners-court.csv`
- Countywide constitutional-office roster: `data/raw/harris-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/harris-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/harris-county/tigerweb-county-48201.geojson`
- Raw Commissioner precinct snapshot: `data/raw/harris-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/harris_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/harris_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/harris_county_commissioner_precincts.geojson`
- Regression test: `tests/test_harris_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-harris-county.yml`

## Result

Harris County now contains ten scoped elected offices represented by five verified geometries: one countywide Census feature shared by six countywide offices and four current official Commissioner precinct polygons. The release preserves the Tax Assessor-Collector transition, the Precinct 4 legacy URL, and the obsolete 2011-boundary item without weakening current-officeholder or geometry validation.
