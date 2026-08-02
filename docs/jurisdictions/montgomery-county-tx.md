# Montgomery County, Texas — Complete County Schema

## Status

Verified release package. First-pass pre-merge validation succeeded in Montgomery County workflow run #6 and repository workflow run #956.

## Purpose

Montgomery County tests freshness convergence across three independently dated official sources. The Elections roster was revised February 18, 2026, the public `Look Up My Commissioner` application was created February 26, 2026, and the County Commissioner Precincts dataset was refreshed April 24, 2026. All three converge on the same current four-precinct structure and roster-bearing GIS layer.

## Jurisdiction identity

- Official name: Montgomery County
- State: Texas
- Jurisdiction type: county
- County FIPS: `339`
- Census GEOID: `48339`
- Representation model: one County Judge elected countywide, four Commissioners elected from precincts, and five additional countywide constitutional officers
- Official roster authority: Montgomery County Elections elected-official and precinct roster revised February 18, 2026
- Commissioner dataset item: `ea4f547b5eec474b8eb6d022afe173b3`
- Public lookup application: `06f7b0e0e2354c8f8e77be19c4256ff5`
- Lookup web map: `8d0ca3edd9bb46f9aea60c99faa54e83`
- Operational layer: `https://services1.arcgis.com/PRoAPGnMSUqvTrzq/arcgis/rest/services/CountyDistrict_Commissioner/FeatureServer/0`
- Stable precinct field: `DISTRICTID`
- Stable source values: `C1`, `C2`, `C3`, `C4`
- Live roster field: `REPNAME1`
- Public precinct-name field: `NAME`
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)

## Current official scope

| Office | Representative geography | Current holder |
|---|---|---|
| County Judge | Countywide | Mark J. Keough |
| County Commissioner Precinct 1 | Precinct 1 | Robert C. Walker |
| County Commissioner Precinct 2 | Precinct 2 | Charlie Riley |
| County Commissioner Precinct 3 | Precinct 3 | Ritch Wheeler |
| County Commissioner Precinct 4 | Precinct 4 | Matt Gray |
| Sheriff | Countywide | Wesley Doolittle |
| County Clerk | Countywide | L. Brandon Steinmann |
| District Clerk | Countywide | Melisa Miller |
| Tax Assessor-Collector | Countywide | Tammy J. McRae |
| County Treasurer | Countywide | Melanie Bush |

All ten holders are current elected incumbents. The Elections roster controls the complete officeholder model. The Commissioner office sites and live `REPNAME1` attributes independently cross-check the four precinct holders.

## Freshness-convergence contract

The release preserves three independently dated official source states:

1. **February 18, 2026:** the Elections roster revision identifies all ten current incumbents.
2. **February 26, 2026:** Montgomery County IT-GIS created the public `Look Up My Commissioner` application.
3. **April 24, 2026:** Montgomery County IT-GIS refreshed the County Commissioner Precincts feature-service item.

The application resolves through web map `8d0ca3edd9bb46f9aea60c99faa54e83` to feature-service item `ea4f547b5eec474b8eb6d022afe173b3`. The dataset resolves to the operational polygon layer listed above. The three source states must continue to agree or trigger explicit review.

## GIS contract

The operational layer publishes exactly four Commissioner precincts:

| Canonical precinct | `DISTRICTID` | `NAME` | `REPNAME1` |
|---|---|---|---|
| 1 | `C1` | Commissioner Precinct 1 | Robert Walker |
| 2 | `C2` | Commissioner Precinct 2 | Charlie Riley |
| 3 | `C3` | Commissioner Precinct 3 | Ritch Wheeler |
| 4 | `C4` | Commissioner Precinct 4 | Matt Gray |

`DISTRICTID` is the stable join field. `REPNAME1` is roster-bearing evidence and must match the independently maintained current roster after approved display-name normalization. `NAME` preserves the public precinct label.

## Turnover guardrails

Precincts 3 and 4 changed after the 2024 election. The release prevents stale or misclassified names from entering the current roster:

- Ritch Wheeler is the current Precinct 3 Commissioner; James Noack is predecessor context only.
- Matt Gray is the current Precinct 4 Commissioner; James Metts is predecessor context only.
- Ryan Gable is Constable Precinct 3, not a County Commissioner.

Candidate filings are preserved only as supplementary selection and turnover context. They do not independently control the current-holder fields.

## Source contract

1. The Elections roster must identify all ten current holders.
2. The Elections roster revision marker must remain February 18, 2026 or receive explicit review.
3. The four Commissioner officeholder values must remain Robert Walker, Charlie Riley, Ritch Wheeler, and Matt Gray.
4. The lookup application must continue to reference web map `8d0ca3edd9bb46f9aea60c99faa54e83` or an explicitly reviewed replacement.
5. The web map must continue to reference dataset item `ea4f547b5eec474b8eb6d022afe173b3` or an explicitly reviewed replacement.
6. The dataset must resolve to `CountyDistrict_Commissioner/FeatureServer/0` or an explicitly reviewed replacement.
7. The layer must remain polygon geometry with fields `DISTRICTID`, `NAME`, and `REPNAME1`.
8. `DISTRICTID` must resolve exactly to `C1` through `C4`.
9. Live `REPNAME1` values must match the current Commissioner roster.
10. Direct GeoJSON regeneration must match the committed raw and canonical snapshots.
11. Six countywide offices must share only the Census county feature.
12. Every normalized row must join exactly one canonical feature.

## Stable identifiers

```text
TX:county:montgomery:countywide:COUNTYWIDE       -> montgomery-county-countywide
TX:county:montgomery:commissioner_precinct:1    -> montgomery-county-commissioner-precinct-1
TX:county:montgomery:commissioner_precinct:2    -> montgomery-county-commissioner-precinct-2
TX:county:montgomery:commissioner_precinct:3    -> montgomery-county-commissioner-precinct-3
TX:county:montgomery:commissioner_precinct:4    -> montgomery-county-commissioner-precinct-4
```

## Release parity

| Layer | Count |
|---|---:|
| Current-officeholder evidence rows | 10 |
| Official source records | 18 |
| Scoped elected offices | 10 |
| Current elected holders | 10 |
| Unique current officeholders | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Validation evidence

- Source-resolution bootstrap: lookup app resolves through web map `8d0ca3edd9bb46f9aea60c99faa54e83` to feature-service item `ea4f547b5eec474b8eb6d022afe173b3`
- Montgomery County workflow run #6: success
- Repository workflow run #956: success
- Automated tests: 76 passed
- Normalized datasets validated: 24 files
- Application-chain and freshness contract: passed
- Live `DISTRICTID`, `NAME`, and `REPNAME1` contract: passed
- Current Commissioner precinct snapshot comparison: passed
- Current Census snapshot comparison: passed
- Geometry joins: passed
- Combined canonical SHA-256: `7cf79b5ccee5534ebc8ec32f9d743d64e23187e05740ff4e30c686b74344c430`

## Release files

- Current roster: `data/raw/montgomery-county/current-elected-offices.csv`
- Source manifest: `data/raw/montgomery-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/montgomery-county/tigerweb-county-48339.geojson`
- Raw Commissioner precinct snapshot: `data/raw/montgomery-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/montgomery_county_elected_offices.csv`
- Canonical county geometry: `data/geojson/montgomery_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/montgomery_county_commissioner_precincts.geojson`
- Regression test: `tests/test_montgomery_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-montgomery-county.yml`

## Result

Montgomery County contains ten scoped elected offices represented by five geometries. The proof combines a current Elections-controlled roster, two recent public GIS publication events, a roster-bearing operational layer, explicit turnover exclusions, stable precinct joins, and exact canonical geometry regeneration.
