# Miami-Dade canonical OCDID correction

## Problem

Batch Pilot target `BP25-012` requested the exact OCD division ID:

```text
ocd-division/country:us/state:fl/county:miami_dade
```

That identifier does not exist in the upstream source, so the target was correctly reported as `upstream_target_not_found`.

## Source finding

The maintained OCD Division IDs sources use the hyphenated county segment:

```text
ocd-division/country:us/state:fl/county:miami-dade
```

The Florida local-government source also places all 13 county commission districts and all 9 school-board districts beneath the `county:miami-dade` prefix.

This is an incorrect exact selector in the manifest, not a fuzzy-name resolution problem or a classification gap.

## Resolution

The manifest now requests the canonical hyphenated OCDID. A focused regression test prevents the obsolete underscore form from returning.

No authoritative override, fuzzy matching rule, or target-only generator patch was added.

## Verified result

The enforced Batch Pilot workflow generated two identical 25-target reports.

For Miami-Dade County:

- match status: `matched`
- resolved OCDID: `ocd-division/country:us/state:fl/county:miami-dade`
- inferred classification: `government`
- generation status: `generated`
- exception class: none
- Division and Jurisdiction YAML: generated
- enrichment status: `partial`, because the validation sheet did not provide a matching enrichment row

The known-archetype result increased from `12/15` to `13/15` for both automatic classification and automatic generation. All 25 targets remained deterministic, and the strict six-fixture gate remained green.

Detailed evidence is stored at:

```text
evidence/batch-pilot-known-archetypes/2026-08-02/miami-dade.json
```
