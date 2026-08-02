# El Paso County, Texas — Complete County Schema

## Status

Release candidate pending permanent El Paso County and repository-wide validation.

## Purpose

El Paso County tests a complete nine-office county release with bilingual source context, a current-officeholder alias, and a county-owned portal web map that must be resolved to its operational Commissioner precinct layer.

## Jurisdiction identity

- Official name: El Paso County
- State: Texas
- Jurisdiction type: county
- County FIPS: `141`
- Census GEOID: `48141`
- Representation model: one County Judge elected countywide, four Commissioners elected from precincts, and four additional countywide constitutional officers
- Official roster authority: El Paso County Elections Department elected-officials directory
- Official GIS landing page: El Paso County GIS
- Portal item ID: `0b4e626d91684cecb1e35828cf52092f`
- App-resolved operational layer: `https://maps.epcounty.com/arcgis/rest/services/Website_Basemap/MapServer/10`
- Stable precinct field: `Precinct`
- Stable precinct values: `1`, `2`, `3`, `4`
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)

## Current official scope

| Office | Representative geography | Current holder |
|---|---|---|
| County Judge | Countywide | Ricardo A. Samaniego |
| County Commissioner Precinct 1 | Precinct 1 | Jacqueline “Jackie” Butler |
| County Commissioner Precinct 2 | Precinct 2 | David Stout |
| County Commissioner Precinct 3 | Precinct 3 | Iliana Holguin |
| County Commissioner Precinct 4 | Precinct 4 | Sergio Coronado |
| Sheriff | Countywide | Oscar Ugarte |
| County Clerk | Countywide | Delia Briones |
| District Clerk | Countywide | Norma Favela Barceleau |
| Tax Assessor-Collector | Countywide | Ruben P. Gonzalez |

All nine holders are current elected incumbents. The official county-office structure does not list a County Treasurer, so the release does not create a vacancy or officeholder record for that role.

## Alias contract

The official Elections Department directory lists the Precinct 1 Commissioner as `Jacqueline Butler`. The official Precinct 1 office page displays `Jackie Butler`. These are treated as two official display forms for the same current officeholder:

- canonical evidence value: `Jacqueline Butler`
- official office-page alias: `Jackie Butler`

The alias is preserved in evidence, manifest notes, normalized notes, regression coverage, and documentation.

## Bilingual source contract

The Precinct 3 office page publishes its mission in English and Spanish. The Elections Department also publishes Spanish-language Commissioner map pages. The release preserves these sources and their original language; it does not translate source attributes or substitute translated labels for canonical identifiers.

## Portal and geometry contract

The county GIS page links the embedded `EP Commissioner Precincts` web map. Portal item `0b4e626d91684cecb1e35828cf52092f` resolves to:

`https://maps.epcounty.com/arcgis/rest/services/Website_Basemap/MapServer/10`

The operational layer supplies:

- polygon geometry
- stable field `Precinct`
- exactly four values: 1, 2, 3, and 4

The layer controls released Commissioner geometry. Current officeholders remain independently controlled by the Elections directory and office pages.

## Source contract

1. The Elections Department directory must identify all nine current holders.
2. The printable directory must continue to identify `Jacqueline Butler` for Precinct 1.
3. The Precinct 1 page must continue to identify `Jackie Butler` as the same officeholder alias.
4. The Precinct 3 page and Spanish Elections map page must preserve bilingual source context.
5. The GIS landing page must continue linking portal item `0b4e626d91684cecb1e35828cf52092f` or an explicitly reviewed replacement.
6. The portal item must resolve to `Website_Basemap/MapServer/10` or an explicitly reviewed replacement.
7. The operational layer must remain polygon geometry with field `Precinct` and values 1 through 4.
8. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
9. Five countywide offices must share only the Census county feature.
10. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:el_paso:countywide:COUNTYWIDE       -> el-paso-county-countywide
TX:county:el_paso:commissioner_precinct:1    -> el-paso-county-commissioner-precinct-1
TX:county:el_paso:commissioner_precinct:2    -> el-paso-county-commissioner-precinct-2
TX:county:el_paso:commissioner_precinct:3    -> el-paso-county-commissioner-precinct-3
TX:county:el_paso:commissioner_precinct:4    -> el-paso-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 9 |
| Official source records | 18 |
| Scoped elected offices | 9 |
| Current elected holders | 9 |
| Unique current officeholders | 9 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

The source-resolution bootstrap proved that portal item `0b4e626d91684cecb1e35828cf52092f` resolves to `Website_Basemap/MapServer/10` using field `Precinct`. Final exact-head workflow evidence is pending.

## Release files

- Current roster: `data/raw/el-paso-county/current-elected-offices.csv`
- Source manifest: `data/raw/el-paso-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/el-paso-county/tigerweb-county-48141.geojson`
- Raw Commissioner precinct snapshot: `data/raw/el-paso-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/el_paso_county_elected_offices.csv`
- Canonical county geometry: `data/geojson/el_paso_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/el_paso_county_commissioner_precincts.geojson`
- Regression test: `tests/test_el_paso_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-el-paso-county.yml`

## Result

El Paso County contains nine scoped elected offices represented by five geometries. The proof combines a current Elections-controlled roster, bilingual official sources, a one-person naming alias, a county-owned portal source contract, stable precinct identifiers, and exact canonical geometry regeneration.
