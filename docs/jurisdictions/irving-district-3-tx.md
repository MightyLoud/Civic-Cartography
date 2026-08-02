# Irving, Texas — District 3 Runoff Proof

## Purpose

Irving City Council Single-Member District 3 is the first Civic Cartography proof for a two-stage runoff election. The bounded release preserves the May 2, 2026 general-election field, the June 13 runoff pair, and the final winner while joining both stages to one official district polygon.

## Jurisdiction identity

- Official name: City of Irving
- State: Texas
- County context: Dallas County
- Jurisdiction type: municipality
- Geography model: one single-member council-district feature
- Election model: majority-required general election followed by a two-candidate runoff when no candidate receives a majority
- Geometry source: City of Irving `CityCouncilDistricts2022` ArcGIS feature layer used for the 2026 election
- Source district field: `DISTRICTID`

## 2026 election stages

### May 2 general election

| Candidate | Vote share | Stage result |
|---|---:|---|
| Abdul Khabeer | 35.02% | Advanced to runoff |
| Kejal Patel | 32.58% | Advanced to runoff |
| Tammam Alwan | 32.40% | Eliminated |

No candidate received a majority, so Irving ordered a runoff between Khabeer and Patel.

### June 13 runoff

| Candidate | Vote share | Final result |
|---|---:|---|
| Abdul Khabeer | 54.85% | Elected |
| Kejal Patel | 45.15% | Not elected |

Five candidate-stage rows are preserved under `data/raw/irving/2026-district-3-election-stages.csv`.

## Stable identifiers

```text
record_id:   TX:municipality:irving:district:3
geometry_id: irving-district-3
```

## Verified release parity

| Layer | Verified count |
|---|---:|
| Candidate-stage evidence rows | 5 |
| Election stages | 2 |
| Official source records | 6 |
| Normalized mapped geography rows | 1 |
| Canonical GeoJSON features | 1 |
| District IDs | 3 |
| Missing joins | 0 |
| Extra joins | 0 |

The normalized row is approved with `parity_ok = TRUE`.

## Source and QA rules

1. Preserve all three May candidates even after the runoff pair is known.
2. Preserve May 2 and June 13 as separate election stages.
3. Preserve advancement, elimination, and final-result status separately.
4. Do not map Irving citywide; only registered voters in Single-Member District 3 could vote in this race.
5. Fetch exactly `DISTRICTID = 3` from the official City of Irving feature layer.
6. Verify that the source attributes identify `NAME = District 3` and `REPNAME = Abdul Khabeer` before publication.
7. Keep the raw ArcGIS response separate from canonical map-ready GeoJSON.
8. The canonical feature carries `geometry_id = irving-district-3` and matching `record_id = TX:municipality:irving:district:3`.
9. Current-source drift fails CI when geometry, the district ID, stable source attributes, or the canonical join changes.
10. Mayor and Districts 5 and 6 remain outside this bounded release.

## Release result

The two election stages, raw official geometry, normalized record, canonical feature, approved QA, and one-to-one geometry join are complete. The release is eligible for merge and Jurisdiction Portfolio registration after the final verified head passes CI.
