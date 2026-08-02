# Tarrant County, Texas — Commissioners Court and Countywide Constitutional Roles

## Status

Verified ten-role release package. Pre-merge validation succeeded in Tarrant County workflow run #18 and repository workflow run #649 after one unrelated TIGERweb retry.

## Purpose

Tarrant County tests two independent civic-data problems in one county model. Its Commissioner precinct geometry requires an explicit source hierarchy because multiple official county layers disagree, and its countywide office structure includes an abolished elected County Treasurer office whose duties now belong to the appointed County Auditor. The release also preserves stale official pages naming former Commissioners and the former Tax Assessor-Collector without allowing those pages to control current data.

## Jurisdiction identity

- Official name: Tarrant County
- State: Texas
- Jurisdiction type: county
- County FIPS: `439`
- Census GEOID: `48439`
- Representation model: five countywide roles carried by separately elected officials, one countywide role carried by the appointed County Auditor, and four Commissioners elected from precincts
- Scoped roles: ten
- Separately elected positions in scope: nine
- Unique current officeholders: ten
- County geometry source: U.S. Census Bureau TIGERweb Current Counties (`MapServer/82`)
- Controlling precinct geometry source: Tarrant County Elections `BondProject/BondProjects/MapServer/3`
- Controlling layer description: Commissioner precinct boundaries effective beginning June 3, 2025
- Stable precinct field: `District_N`
- Stable precinct values: `1`, `2`, `3`, `4`
- Geometry-only source: no officeholder field is used or inferred

## Current official scope

| Role | Representative geography | Current holder | Selection structure |
|---|---|---|---|
| County Judge | Countywide | Tim O’Hare | Separately elected |
| Sheriff | Countywide | Bill E. Waybourn | Separately elected |
| County Clerk | Countywide | Mary Louise Nicholson | Separately elected |
| District Clerk | Countywide | Thomas A. Wilder | Separately elected |
| Tax Assessor-Collector | Countywide | Rick Barnes | Separately elected |
| County Treasurer duties | Countywide | Kimberly M. Buchanan, County Auditor | Appointed Auditor; Treasurer office abolished |
| Commissioner Precinct 1 | Precinct 1 | Roderick Miles Jr. | Separately elected from precinct |
| Commissioner Precinct 2 | Precinct 2 | Alisa Simmons | Separately elected from precinct |
| Commissioner Precinct 3 | Precinct 3 | Matt Krause | Separately elected from precinct |
| Commissioner Precinct 4 | Precinct 4 | Manny Ramirez | Separately elected from precinct |

The current elected-official directory controls the nine separately elected positions. Individual official office pages independently identify the four additional countywide elected officeholders. The County Auditor page controls the appointed Auditor role.

## Abolished County Treasurer structure

Tarrant County's official Auditor page states that the County Treasurer office was abolished by constitutional amendment and its duties transferred to the County Auditor in 1983. The County Auditor is appointed by the District Judges for a two-year term rather than elected countywide. The same page identifies Kimberly M. Buchanan as the current County Auditor.

The release therefore scopes `County Treasurer duties` as a current countywide role but does not count it as a separately elected position. It shares the existing Tarrant County countywide geometry with the five elected countywide roles.

The official Bail Bond Board page provides an independent structural cross-check: it quotes the statutory exception for counties with no County Treasurer and lists the County Auditor among current board members.

## Tax Assessor-Collector transition and stale pages

Current county and Tax Office pages identify Rick Barnes as Tax Assessor-Collector. An official Tax Office release dated January 13, 2025 also identifies Rick D. Barnes in office, establishing the transition by the beginning of 2025.

Two still-live official pages retain Wendy Burgess:

1. A Tarrant County Elections Commission page modified January 16, 2026 lists Wendy Burgess as Tax Assessor-Collector and commission secretary.
2. A Tax Office test FAQ retains Wendy Burgess in payment instructions while its 2026 footer identifies Rick Barnes.

Both pages are preserved as stale transition evidence and do not control the current officeholder value.

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

## Stale Commissioner roster handling

The still-live county page at `https://www.tarrantcountytx.gov/en/county-judge/for-redirect-purpose/Maps.html` lists Roy C. Brooks for Precinct 1 and Gary Fickes for Precinct 3. Current official pages identify Roderick Miles Jr. and Matt Krause. The old page remains in the source manifest as stale roster evidence and does not control current officeholder values.

## Source contract

1. The controlling June 3, 2025 layer must remain available and return exactly four polygon features.
2. `District_N` must resolve to values `1`, `2`, `3`, and `4`.
3. Direct GeoJSON regeneration from the controlling layer must match the committed raw and canonical snapshots.
4. The undated general layer must remain separately documented; if it converges with or replaces the controlling layer, the source hierarchy must be reviewed.
5. The explicit 2010 service must remain documented but never control current geometry.
6. Current elected officeholders must come from current official directories and office pages, not GIS or stale pages.
7. Rick Barnes must remain the current Tax Assessor-Collector unless controlling sources change; Wendy Burgess references are stale evidence.
8. County Treasurer duties must remain associated with the appointed County Auditor unless the county's constitutional structure changes.
9. All six countywide roles must share one Census county feature without duplicate normalized rows.
10. Every normalized row must join exactly one canonical feature.

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
| Current role evidence rows | 10 |
| Official source records | 22 |
| Scoped roles | 10 |
| Separately elected positions | 9 |
| Unique current officeholders | 10 |
| Normalized geography rows | 5 |
| Canonical GeoJSON features | 5 |
| Countywide features | 1 |
| Commissioner-precinct features | 4 |
| Missing joins | 0 |
| Extra joins | 0 |

All five normalized records use `qa_status = approved` and `parity_ok = TRUE`.

## Geometry preservation

The countywide and Commissioner precinct GeoJSON files are unchanged by this extension. The existing canonical digest remains:

`36a5c53bd999162d8837de7218a89f146949eaf552feca56abddd557054cb263`

## Validation evidence

- Tarrant County workflow run #18: success
- Repository workflow run #649: success after retrying an unrelated transient TIGERweb non-JSON response for Olmos Park
- Automated tests: 57 passed
- Normalized datasets validated: 19 files
- Controlling ArcGIS metadata hierarchy: passed
- Four-district geometry-source divergence: passed
- Current controlling precinct snapshot comparison: passed
- Current Census snapshot comparison: passed
- Countywide role, election-count, Treasurer-abolition, and tax-transition regression: passed
- Geometry joins: passed
- Combined canonical SHA-256: `36a5c53bd999162d8837de7218a89f146949eaf552feca56abddd557054cb263`

## Release files

- Current Commissioners Court roster: `data/raw/tarrant-county/current-commissioners-court.csv`
- Current countywide role evidence: `data/raw/tarrant-county/current-countywide-roles.csv`
- Source manifest: `data/raw/tarrant-county/source-manifest.csv`
- Raw Census county snapshot: `data/raw/tarrant-county/tigerweb-county-48439.geojson`
- Raw Commissioner precinct snapshot: `data/raw/tarrant-county/commissioner-precincts-1-4.geojson`
- Normalized records: `data/normalized/tarrant_county_commissioners_court.csv`
- Canonical county geometry: `data/geojson/tarrant_county_countywide.geojson`
- Canonical Commissioner precinct geometry: `data/geojson/tarrant_county_commissioner_precincts.geojson`
- Regression test: `tests/test_tarrant_county_roster.py`
- Permanent drift workflow: `.github/workflows/validate-tarrant-county.yml`

## Result

Tarrant County now models ten scoped roles represented by five geometries. Six countywide roles share one Census feature, including the appointed Auditor carrying abolished Treasurer duties; Commissioners Precincts 1 through 4 remain on the explicitly dated 2025 boundaries. The release preserves stale tax, roster, and geometry evidence without allowing any stale source to weaken the current model.
