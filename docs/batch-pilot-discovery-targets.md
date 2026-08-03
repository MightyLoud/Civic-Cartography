# Batch Pilot discovery targets

## Decision

The four Batch Pilot 25 discovery targets are maintained reusable generation cases rather than explicit exceptions:

| Target | Resolution | Classification |
|---|---|---|
| BP25-019 — Bay Area Rapid Transit District | authoritative override | `transit_authority` |
| BP25-020 — Metropolitan Water Reclamation District of Greater Chicago | authoritative override retaining `state:il/sewer:mwrd` | `special_purpose_district` |
| BP25-021 — Port of Seattle | authoritative override | `special_purpose_district` |
| BP25-025 — Metropolitan Government of Nashville and Davidson County | canonical county+place alias | `government` |

No fuzzy matching, handcrafted generated YAML, or target-only production patch is used.

## Source findings

### BART

The pinned OCD identifier inputs contain no BART root record. Official BART materials identify the legal San Francisco Bay Area Rapid Transit District as a California public agency created in 1957 and governed by an elected nine-member Board under the San Francisco Bay Area Rapid Transit District Act.

The maintained Division ID is:

`ocd-division/country:us/state:ca/special_district:san_francisco_bay_area_rapid_transit_district`

### Metropolitan Water Reclamation District

The pinned OCD source already contains:

`ocd-division/country:us/state:il/sewer:mwrd`

under the short name `Metropolitan Water Reclamation District`. Official MWRD materials identify the full public name and an independent regional special-purpose government governed by nine commissioners elected countywide in Cook County. The existing upstream OCDID is retained; only authoritative classification, naming, and source metadata are added.

### Port of Seattle

The pinned OCD identifier inputs contain no Port of Seattle root record. Official Port materials identify a Washington public agency and port district governed by five commissioners elected at large by King County voters under RCW Chapter 53.

The maintained Division ID is:

`ocd-division/country:us/state:wa/special_district:port_of_seattle`

### Nashville–Davidson

The pinned OCD source contains both:

- `ocd-division/country:us/state:tn/county:davidson`
- `ocd-division/country:us/state:tn/place:nashville`

and explicitly advises that the county identifier is preferable for government statistics. Official Metro materials identify one city-county consolidated government created in 1963. Davidson County is therefore the canonical member, while both geographic Divisions are preserved.

The upstream Nashville place label also embeds a long advisory note. The canonical-alias registry now supports exact per-member display names so the place Division uses `Nashville` without changing its OCDID or applying a fuzzy rule.

## Confirmed generation

The enforced two-run Batch Pilot generated:

- BART: one Division and one `transit_authority` Jurisdiction.
- MWRD: one Division and one `special_purpose_district` Jurisdiction.
- Port of Seattle: one Division and one `special_purpose_district` Jurisdiction.
- Nashville–Davidson: two Divisions and exactly one shared `government` Jurisdiction.

All four targets have:

- `match_status = matched`
- expected classification matched
- `generation_status = generated`
- no exception class
- no review reason

Validation enrichment is `partial` because the optional validation sheet has no matching enrichment rows. Required Division and Jurisdiction generation is complete.

## Batch result

- discovery targets classified and generated: **4/4**
- known-archetype targets classified and generated: **15/15**
- regression fixtures: **6/6**
- deterministic targets: **25/25**
- complete reports identical: **true**
- target-only production patches: **0**
- overall gate: **passed**

Evaluation ID: `ffeb1f9b74c050588a43`  
Run ID: `467baa4b6df060e70439`

Machine-readable paths, hashes, and workflow evidence are stored at:

`evidence/batch-pilot-discovery/2026-08-02/discovery-targets.json`
