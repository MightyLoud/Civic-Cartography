# Poth ISD, Texas — Canceled Election Proof

## Release status

Poth Independent School District is the completed Civic Cartography proof for a canceled school-board election in which all candidates were certified unopposed. The bounded scope is the three trustee seats scheduled for May 2, 2026.

## Jurisdiction identity

- Official name: Poth Independent School District
- State: Texas
- County context: Wilson County
- Jurisdiction type: school district
- Census unified-school-district GEOID: `4835550`
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

## Released identifiers

```text
record_id:   TX:school_district:poth-isd:at_large:DISTRICTWIDE
geometry_id: poth-isd-districtwide
```

## Released artifacts

- Candidate/declaration evidence: `data/raw/poth-isd/2026-trustee-declarations.csv`
- Source manifest: `data/raw/poth-isd/source-manifest.csv`
- Raw Census snapshot: `data/raw/poth-isd/tigerweb-unified-school-district-4835550.geojson`
- Normalized record: `data/normalized/poth_isd_2026.csv`
- Canonical geometry: `data/geojson/poth_isd_districtwide.geojson`

## Verified parity

| Layer | Released count |
|---|---:|
| Candidate/declaration evidence rows | 3 |
| Official source records | 5 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| Missing joins | 0 |
| Extra joins | 0 |

The normalized record has `qa_status = approved` and `parity_ok = TRUE`.

## Source and QA rules

1. Treat the canceled election as a verified outcome, not as missing results.
2. Preserve all three declared-elected candidates and normalize spelling to official oath/current-board evidence.
3. Do not create separate trustee polygons; Poth ISD elects its board at large.
4. Resolve exactly one current Census unified-school-district feature whose official name contains `Poth`.
5. Preserve Census GEOID `4835550` and fail CI if the current source resolves differently.
6. Keep the raw TIGERweb response separate from canonical map-ready GeoJSON.
7. Require `geometry_id = poth-isd-districtwide` and its matching `record_id` on the canonical feature.
8. Fail CI when geometry, GEOID, stable source attributes, or the canonical join changes.
9. Keep the four trustee terms scheduled for 2027 outside this bounded release.

## Completion result

The raw declaration evidence, source manifest, normalized record, raw Census snapshot, canonical feature, approved QA, one-to-one join, and live Census drift comparison are complete and green. The release is ready to merge and register in the Jurisdiction Portfolio.
