# Coppell ISD, Texas — School District Factory Proof

## Status

Released candidate. The complete raw → normalized → QA → GeoJSON chain passed permanent read-only validation in GitHub Actions run #132.

## Purpose

Coppell Independent School District is the second Civic Cartography `school_district` release. The bounded election scope is Trustee Places 4 and 5 from the May 2, 2026 election.

## Jurisdiction identity

- Official name: Coppell Independent School District
- State: Texas
- County context: Dallas and Denton counties
- Jurisdiction type: school district
- Census GEOID: `4815210`
- Geometry model: one unified-school-district feature
- Election model: trustees run for numbered places but represent the entire district at large
- Geometry source: U.S. Census Bureau TIGERweb Current Unified School Districts (`MapServer/14`)

## 2026 bounded election context

| Place | Final-ballot candidates | Official winner |
|---|---:|---|
| 4 | 1 | Ranna Raval |
| 5 | 2 | Kevin Chaka |

The official filing page also records Carly Waters as withdrawn from Place 5. Four filing events are preserved under `data/raw/coppell-isd/2026-trustee-filing-events.csv`; three reached the final ballot.

## Released identifiers

```text
record_id:   TX:school_district:coppell-isd:at_large:DISTRICTWIDE
geometry_id: coppell-isd-districtwide
```

## Completed parity

| Layer | Count |
|---|---:|
| Filing-event evidence rows | 4 |
| Final-ballot candidates | 3 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

The normalized record has `qa_status = approved` and `parity_ok = TRUE`.

## Release files

- Filing-event evidence: `data/raw/coppell-isd/2026-trustee-filing-events.csv`
- Source manifest: `data/raw/coppell-isd/source-manifest.csv`
- Raw Census geometry: `data/raw/coppell-isd/tigerweb-unified-school-district-4815210.geojson`
- Normalized record: `data/normalized/coppell_isd_2026.csv`
- Canonical geometry: `data/geojson/coppell_isd_districtwide.geojson`

## Source and QA rules

1. Preserve the withdrawn filing instead of silently reducing the source history to the final ballot.
2. Do not create separate polygons for Places 4 and 5; Coppell ISD confirms each trustee represents the district at large.
3. Resolve exactly one current Census unified-school-district feature whose official name contains `Coppell`.
4. Preserve the returned Census GEOID `4815210`.
5. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
6. The canonical feature carries `geometry_id = coppell-isd-districtwide` and its matching `record_id`.
7. CI regenerates the official feature and fails on geometry, GEOID, stable source-attribute, or canonical-join drift.
8. Trustee Places 1–3 and 6–7 remain outside this bounded election release.

## Result

Coppell ISD proves the Eanes school-district pattern repeats without redesign while preserving a withdrawn filing that did not reach the final ballot.
