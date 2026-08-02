# Bexar County, Texas — Commissioners Court and Countywide Constitutional Roles

## Status

Ten-role release candidate pending final Bexar County and repository-wide validation.

## Purpose

Bexar County first proved the county template transfers cleanly through a dedicated MapServer that directly exposes district identity, current Commissioner names, office websites, and GeoJSON geometry. This extension tests a different countywide-office structure: four additional elected offices plus County Treasurer duties consolidated into the elected County Clerk after voters abolished the separate Treasurer office.

## Jurisdiction identity

- Official name: Bexar County
- State: Texas
- Jurisdiction type: county
- County FIPS: `029`
- Census GEOID: `48029`
- Representation model: six countywide roles plus four Commissioners elected from precincts
- Separately elected positions in scope: nine
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Precinct geometry source: Bexar County GIS `CommissionerPrecincts/MapServer/0`
- Stable precinct field: `Comm`
- Live Commissioner field: `ComName`
- Source website field: `Website`
- Stable precinct values: `1`, `2`, `3`, `4`

## Current official scope

| Office or role | Representative geography | Officeholder | Selection structure |
|---|---|---|---|
| County Judge | Countywide | Peter Sakai | Separately elected |
| Sheriff | Countywide | Javier Salazar | Separately elected |
| County Clerk | Countywide | Lucy Adame-Clark | Separately elected |
| District Clerk | Countywide | Gloria A. Martinez | Separately elected |
| Tax Assessor-Collector | Countywide | Albert Uresti | Separately elected |
| County Treasurer duties | Countywide | Lucy Adame-Clark | Consolidated into County Clerk; not separately elected |
| Commissioner Precinct 1 | Precinct 1 | Rebeca Clay-Flores | Separately elected from precinct |
| Commissioner Precinct 2 | Precinct 2 | Justin Rodriguez | Separately elected from precinct |
| Commissioner Precinct 3 | Precinct 3 | Grant Moody | Separately elected from precinct |
| Commissioner Precinct 4 | Precinct 4 | Tommy Calvert | Separately elected from precinct; GIS alias `Tommy Calvert Jr.` |

## Treasurer abolition and consolidated duties

Texas voters adopted Proposition 4 on November 6, 1984, abolishing the office of County Treasurer in Bexar and Collin counties. Bexar County's current elected-official directory therefore does not list a separately elected Treasurer. The official County Clerk biography states that Lucy Adame-Clark serves as Bexar County Treasurer.

The release models this accurately:

1. County Treasurer duties are a distinct countywide role for evidence and scope reporting.
2. Lucy Adame-Clark is counted once as a unique person while holding the elected County Clerk position and performing the consolidated Treasurer role.
3. The Treasurer role does not create a second normalized countywide row or a second geometry.
4. The public-elected-office count remains nine, while the scoped-role count is ten.

## Commissioner source handling

The Precinct 4 suffix variation is treated as a compatible naming alias. The website roster, individual office page, GIS website URL, and represented precinct identify the same officeholder.

A still-live Bexar County elections-finance page lists Nelson W. Wolff as County Judge and Sergio "Chico" Rodriguez, Paul Elizondo, Kevin Wolff, and Tommy Adkisson as Commissioners. That page is retained in the source manifest as an obsolete historical roster and does not control any current officeholder field.

## GIS source contract

1. The official layer must remain available at `https://maps.bexar.org/arcgis/rest/services/CommissionerPrecincts/MapServer/0`.
2. The layer must return exactly four polygon features with `Comm` values `1` through `4`.
3. `ComName` must resolve to Rebeca Clay-Flores, Justin Rodriguez, Grant Moody, and Tommy Calvert Jr.
4. `Website` must resolve to the four official Commissioner office URLs.
5. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
6. All six countywide roles must share the single Census county feature.
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
| Current-officeholder and role evidence rows | 10 |
| New countywide role evidence rows | 5 |
| Official source records | 18 |
| Scoped office roles | 10 |
| Separately elected positions | 9 |
| Unique current officeholders | 9 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Commissioners Court roster: `data/raw/bexar-county/current-commissioners-court.csv`
- Countywide constitutional and consolidated roles: `data/raw/bexar-county/current-countywide-constitutional-offices.csv`
- Source manifest: `data/raw/bexar-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/bexar-county/tigerweb-county-48029.geojson`
- Raw Commissioner precinct snapshot: `data/raw/bexar-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/bexar_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/bexar_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/bexar_county_commissioner_precincts.geojson`
- Regression test: `tests/test_bexar_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-bexar-county.yml`

## Result

Bexar County contains ten scoped office roles represented by five verified geometries. Six countywide roles share one Census feature, including Treasurer duties consolidated into the County Clerk, while Commissioners Precincts 1–4 retain four official GIS polygons. No geometry changes are required for the extension.
