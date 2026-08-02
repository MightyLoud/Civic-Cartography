# Poth ISD, Texas — Canceled Election Proof

## Purpose

Poth Independent School District is the Civic Cartography proof for a canceled school-board election in which all candidates were certified unopposed. The bounded scope is the three trustee seats scheduled for May 2, 2026.

## Jurisdiction identity

- Official name: Poth Independent School District
- State: Texas
- County context: Wilson County
- Jurisdiction type: school district
- Geometry model: one unified-school-district feature
- Election model: seven trustees elected at large using cumulative voting
- 2026 election status: canceled after certification of unopposed candidates
- Geometry source: U.S. Census Bureau TIGERweb Current Unified School Districts (`MapServer/14`)

## 2026 bounded election context

| Candidate | Filing/result status |
|---|---|
| William Eckel | Unopposed; declared elected |
| Clint Garza | Unopposed; declared elected |
| Tami Ramzinski | Unopposed; declared elected |

The three declaration records are preserved under `data/raw/poth-isd/2026-trustee-declarations.csv`.

## Planned identifiers

```text
record_id:   TX:school_district:poth-isd:at_large:DISTRICTWIDE
geometry_id: poth-isd-districtwide
```

## Target parity

| Layer | Expected count |
|---|---:|
| Candidate/declaration evidence rows | 3 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

## Source and QA rules

1. Treat the canceled election as a verified outcome, not as missing results.
2. Preserve all three declared-elected candidates and normalize spelling to official oath/current-board evidence.
3. Do not create separate trustee polygons; Poth ISD elects its board at large.
4. Resolve exactly one current Census unified-school-district feature whose official name contains `Poth`.
5. Capture and preserve the returned Census GEOID rather than assuming it.
6. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
7. The canonical feature must carry `geometry_id = poth-isd-districtwide` and its matching `record_id`.
8. Current-source drift must fail CI when geometry, GEOID, stable source attributes, or the canonical join changes.
9. The four trustee terms scheduled for 2027 remain outside this bounded release.

## Completion rule

Poth ISD is not complete until candidate/declaration evidence, raw Census geometry, one normalized record, one canonical feature, approved QA, `parity_ok = TRUE`, green CI, a merged pull request, and the Jurisdiction Portfolio all agree.
