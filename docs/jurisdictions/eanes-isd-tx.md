# Eanes ISD, Texas — School District Proof

## Purpose

Eanes Independent School District is the first Civic Cartography release for the `school_district` jurisdiction type. The bounded election scope is Trustee Places 1, 2, and 3 from the May 2, 2026 election.

## Jurisdiction identity

- Official name: Eanes Independent School District
- State: Texas
- County context: Travis County
- Jurisdiction type: school district
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

## Planned identifiers

```text
record_id:   TX:school_district:eanes-isd:at_large:DISTRICTWIDE
geometry_id: eanes-isd-districtwide
```

## Target parity

| Layer | Expected count |
|---|---:|
| Candidate evidence rows | 7 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Preserve all seven candidates even though the map has one districtwide feature.
2. Do not create separate polygons for Trustee Places 1–3; Eanes ISD confirms all positions are at large.
3. Resolve exactly one current Census unified-school-district feature whose official name contains `Eanes`.
4. Capture and preserve the returned Census GEOID rather than assuming it.
5. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
6. The canonical feature must carry `geometry_id = eanes-isd-districtwide` and its matching `record_id`.
7. Current-source drift must fail CI when geometry, GEOID, stable source attributes, or the canonical join changes.
8. Trustee Places 4–7 remain outside this bounded election release.

## Completion rule

Eanes ISD is not complete until raw candidate evidence exists, raw Census geometry exists, one normalized record exists, one canonical feature exists, QA is approved, `parity_ok = TRUE`, CI is green, the pull request is merged, and the Jurisdiction Portfolio reflects the release.
