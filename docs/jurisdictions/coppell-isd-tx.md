# Coppell ISD, Texas — School District Factory Proof

## Purpose

Coppell Independent School District is the second Civic Cartography `school_district` release candidate. The bounded election scope is Trustee Places 4 and 5 from the May 2, 2026 election.

## Jurisdiction identity

- Official name: Coppell Independent School District
- State: Texas
- County context: Dallas and Denton counties
- Jurisdiction type: school district
- Geometry model: one unified-school-district feature
- Election model: trustees run for numbered places but represent the entire district at large
- Geometry source: U.S. Census Bureau TIGERweb Current Unified School Districts (`MapServer/14`)

## 2026 bounded election context

| Place | Final-ballot candidates | Official winner |
|---|---:|---|
| 4 | 1 | Ranna Raval |
| 5 | 2 | Kevin Chaka |

The official filing page also records Carly Waters as withdrawn from Place 5. Four filing events are preserved under `data/raw/coppell-isd/2026-trustee-filing-events.csv`; three reached the final ballot.

## Planned identifiers

```text
record_id:   TX:school_district:coppell-isd:at_large:DISTRICTWIDE
geometry_id: coppell-isd-districtwide
```

## Target parity

| Layer | Expected count |
|---|---:|
| Filing-event evidence rows | 4 |
| Final-ballot candidates | 3 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Preserve the withdrawn filing instead of silently reducing the source history to the final ballot.
2. Do not create separate polygons for Places 4 and 5; Coppell ISD confirms each trustee represents the district at large.
3. Resolve exactly one current Census unified-school-district feature whose official name contains `Coppell`.
4. Capture and preserve the returned Census GEOID rather than assuming it.
5. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
6. The canonical feature must carry `geometry_id = coppell-isd-districtwide` and its matching `record_id`.
7. Current-source drift must fail CI when geometry, GEOID, stable source attributes, or the canonical join changes.
8. Trustee Places 1–3 and 6–7 remain outside this bounded election release.

## Completion rule

Coppell ISD is not complete until filing evidence, raw Census geometry, one normalized record, one canonical feature, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
