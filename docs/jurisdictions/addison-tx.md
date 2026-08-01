# Addison, Texas — Jurisdiction #2

## Purpose

Addison is the factory-proof repetition of the Civic Cartography pipeline. It reuses the Olmos Park source → normalized → QA → GeoJSON contract without introducing a broader framework.

## Jurisdiction identity

- Official name: Town of Addison
- State: Texas
- Place FIPS: `01240`
- Census GEOID: `4801240`
- Jurisdiction type: municipality
- Municipal type: town
- Geometry model: one incorporated-place citywide feature
- Election model: at-large, multi-seat

## 2026 election context

The May 2, 2026 election filled three City Council seats. Five candidates filed:

1. Schnell Blanton — elected
2. Chris DeFrancisco — elected
3. Howard Freed — not elected
4. Darren Gardner — elected
5. Trish Stuart — not elected

The Town states that Addison has a Mayor and six council members, all elected at large. Council-district polygons do not exist for this scope and were not invented.

## Published identifiers

```text
record_id:   TX:municipality:addison:at_large:CITYWIDE
geometry_id: addison-citywide
```

## Completed parity

| Layer | Count |
|---|---:|
| Candidate filing rows | 5 |
| Elected candidates in the 2026 contest | 3 |
| Official source records | 4 |
| Normalized mapped geography rows | 1 |
| GeoJSON features | 1 |
| Missing geometry joins | 0 |
| Extra geometry joins | 0 |

## QA result

- `qa_status = approved`
- `parity_ok = TRUE`
- Current TIGERweb incorporated-place boundary matches the committed raw and canonical snapshots.
- The normalized `addison-citywide` geometry ID resolves to exactly one GeoJSON feature and the matching record ID.
- Olmos Park remains protected by the same CI run, proving the second jurisdiction did not weaken the first.

## Name QA note

The TX Data C6 working row used `Tricia Stuart`; the current official election page uses `Trish Stuart`. The repository preserves the official display name and records the working-sheet form as an alias variation rather than silently treating them as separate people.

## Reproducibility

The repository stores:

- the five candidate rows under `data/raw/addison/`;
- the official source manifest;
- the raw Census TIGERweb response for GEOID `4801240`;
- one normalized citywide row under `data/normalized/`;
- one canonical map feature under `data/geojson/`;
- read-only CI checks that regenerate and compare both Addison and Olmos Park against current Census data.

## Completion rule

Addison is complete when the pull request is merged through green CI and the Jurisdiction Portfolio is updated to `RELEASED`.
