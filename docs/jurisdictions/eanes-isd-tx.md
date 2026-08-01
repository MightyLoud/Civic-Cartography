# Eanes ISD, Texas — School District Proof

## Status

Released candidate pending merge. The full Eanes ISD pipeline passed permanent read-only CI in GitHub Actions run #117.

## Purpose

Eanes Independent School District is the first Civic Cartography release for the `school_district` jurisdiction type. The bounded election scope is Trustee Places 1, 2, and 3 from the May 2, 2026 election.

## Jurisdiction identity

- Official name: Eanes Independent School District
- State: Texas
- County context: Travis County
- Jurisdiction type: school district
- Census unified-school-district GEOID: `4817760`
- Geometry model: one unified-school-district feature
- Election model: seven trustees elected at large to three-year terms
- Geometry source: U.S. Census Bureau TIGERweb Current Unified School Districts (`MapServer/14`)

## 2026 bounded election context

| Place | Candidates | Official winner |
|---|---:|---|
| 1 | 3 | Kate Ivers |
| 2 | 2 | Jennifer Blackman |
| 3 | 2 | Diane Hern |

Seven candidate rows are preserved under `data/raw/eanes-isd/2026-trustee-candidates.csv`.

## Released identifiers

```text
record_id:   TX:school_district:eanes-isd:at_large:DISTRICTWIDE
geometry_id: eanes-isd-districtwide
```

## Completed parity

| Layer | Count |
|---|---:|
| Candidate evidence rows | 7 |
| Official source records | 3 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

The normalized record has `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Candidate evidence: `data/raw/eanes-isd/2026-trustee-candidates.csv`
- Source manifest: `data/raw/eanes-isd/source-manifest.csv`
- Raw official geometry: `data/raw/eanes-isd/tigerweb-unified-school-district-4817760.geojson`
- Normalized record: `data/normalized/eanes_isd_2026.csv`
- Canonical geometry: `data/geojson/eanes_isd_districtwide.geojson`

## Source and QA rules

1. Preserve all seven candidates even though the map has one districtwide feature.
2. Do not create separate polygons for Trustee Places 1–3; Eanes ISD confirms all positions are at large.
3. Resolve exactly one current Census unified-school-district feature whose official name contains `Eanes`.
4. Preserve the returned Census GEOID `4817760`; do not infer it from a working sheet.
5. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
6. The canonical feature carries `geometry_id = eanes-isd-districtwide` and its matching `record_id`.
7. CI regenerates the official feature and fails on geometry, GEOID, stable source-attribute, or canonical-join drift.
8. Trustee Places 4–7 remain outside this bounded election release.

## Result

Eanes ISD proves the existing Civic Cartography pattern can support an at-large school board and a unified-school-district boundary without weakening candidate evidence, QA, parity, or source-drift controls.
