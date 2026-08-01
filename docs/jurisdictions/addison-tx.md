# Addison, Texas — Jurisdiction #2

## Purpose

Addison is the factory-proof run for the Civic Cartography pipeline. The work should reuse the Olmos Park source → normalized → QA → GeoJSON contract without introducing a broad new framework.

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

The official Town page states that Addison has a Mayor and six council members, all elected at large. Therefore, council-district polygons do not exist for this scope and must not be invented.

## Planned identifiers

```text
record_id:   TX:municipality:addison:at_large:CITYWIDE
geometry_id: addison-citywide
```

## Target parity

| Layer | Expected count |
|---|---:|
| Candidate filing rows | 5 |
| Elected candidates in the 2026 contest | 3 |
| Normalized mapped geography rows | 1 |
| GeoJSON features | 1 |
| Missing geometry joins | 0 |
| Extra geometry joins | 0 |

## Name QA note

The TX Data C6 working row used `Tricia Stuart`; the current official election page uses `Trish Stuart`. The repository preserves the official display name and records the working-sheet form as an alias variation rather than silently treating them as separate people.

## Next implementation steps

1. Fetch the current TIGERweb incorporated-place boundary for GEOID `4801240`.
2. Commit the raw Census response and canonical `addison-citywide` GeoJSON.
3. Add one approved normalized citywide record.
4. Extend existing CI checks to Addison without weakening the Olmos Park checks.
5. Register the released jurisdiction in the Command Center only after the full chain is green.

## Completion rule

Addison is not complete until raw evidence exists, normalized data exists, QA passes, the GeoJSON join is one-to-one, `parity_ok = TRUE`, CI is green, and the Jurisdiction Portfolio reflects the release.
