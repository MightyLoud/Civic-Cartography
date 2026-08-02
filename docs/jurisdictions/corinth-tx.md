# Corinth, Texas — Mixed General and Special Election Proof

## Purpose

Corinth is the Civic Cartography proof for multiple election types and term lengths occurring in one at-large municipality on the same election date. The bounded scope is the May 2, 2026 Mayor, Council Place 2, and Council Place 5 contests.

## Jurisdiction identity

- Official name: City of Corinth
- State: Texas
- County context: Denton County
- Jurisdiction type: municipality
- Geometry model: one incorporated-place feature
- Election model: Mayor and five numbered council places elected at large
- Geometry source: U.S. Census Bureau TIGERweb Current Incorporated Places (`MapServer/28`)
- Census GEOID: `4816696`

## 2026 bounded election context

| Office | Election type | Candidates | Verified officeholder | Term result |
|---|---|---:|---|---|
| Mayor | General | 1 | Scott Garber | Three-year term through May 2029 |
| Council Place 2 | Special | 1 | Heath Schadegg | Unexpired term through May 2028 |
| Council Place 5 | General | 3 | Kelly Pickens | Three-year term through May 2029 |

Five candidate rows are preserved under `data/raw/corinth/2026-election-candidates.csv`.

## Stable identifiers

```text
record_id:   TX:municipality:corinth:at_large:CITYWIDE
geometry_id: corinth-citywide
```

## Verified parity

| Layer | Verified count |
|---|---:|
| Candidate evidence rows | 5 |
| Scoped offices | 3 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

- `qa_status = approved`
- `parity_ok = TRUE`
- Census GEOID: `4816696`
- Permanent current-source validation: enabled
- GitHub Actions verification: run #162 passed

## Source and QA rules

1. Preserve all five candidates, including both unsuccessful Place 5 candidates.
2. Preserve `General` versus `Special` as a first-class distinction in the raw evidence and normalized notes.
3. Preserve the Place 2 term ending in May 2028; do not assign the regular May 2029 expiration.
4. Do not create separate polygons for Mayor or numbered council places; Corinth elects all council positions at large.
5. Use the official current council roster and official term pages to confirm the resulting officeholders.
6. Fetch the current Census incorporated-place feature by GEOID `4816696`.
7. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
8. The canonical feature carries `geometry_id = corinth-citywide` and its matching `record_id`.
9. Current-source drift fails CI when geometry, GEOID, stable source attributes, or the canonical join changes.

## Release result

Corinth proves that one citywide geography can retain multiple office contests without flattening their election semantics. The general-election offices retain May 2029 term expirations, while the Place 2 special election retains its May 2028 unexpired-term endpoint.
