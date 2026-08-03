# Seattle Public Schools exact lookup

## Decision

Batch Pilot target `BP25-016` keeps the human-facing jurisdiction name **Seattle Public Schools** and uses the exact upstream selector name **Seattle Public Schools**.

This is a maintained exact-name lookup. It is not fuzzy matching.

## Root cause

The previous selector used the legal-style name:

`Seattle School District No. 1`

The pinned Open Civic Data master source instead contains:

- OCDID: `ocd-division/country:us/state:wa/county:king/school_district:seattle_public_schools`
- source name: `seattle public schools`
- federal district identifier: `5307710`
- Washington state district identifier: `17001`

The source label is unique in the pinned national master used by the Batch Pilot run.

## Implementation

The manifest selector is:

```yaml
- target_id: BP25-016
  jurisdiction_name: Seattle Public Schools
  state: wa
  selector:
    type: explicit_lookup
    name: Seattle Public Schools
    resolution_policy: override_or_exception
  expected_classification: school_system
```

The resolver normalizes punctuation and capitalization, then requires an exact maintained-name match. Multiple matches remain an explicit ambiguity failure.

No generator patch, alias-table entry, fuzzy matching rule, or authoritative override was added.

## Confirmed output

The two-run Batch Pilot workflow generated:

- Division: `divisions/wa/local/seattle_public_schools__09e8b756-50d7-5d67-9278-6610241883b3.yaml`
- Jurisdiction: `jurisdictions/wa/local/seattle_public_schools_9a3d5c91-9bfd-50df-86c6-60f3f39dd8b6.yaml`
- Jurisdiction OCDID: `ocd-jurisdiction/country:us/state:wa/county:king/school_district:seattle_public_schools/school_system`
- classification: `school_system`

The target has no exception class and no review reason. Source enrichment remains partial because the validation sheet did not contain a matching enrichment row; this does not block Division or Jurisdiction generation.

## Batch result

- known-archetype classification: `15/15` (`100%`)
- known-archetype generation: `15/15` (`100%`)
- regression fixtures: `6/6`
- deterministic targets: `25/25`
- reports identical: `true`
- target-only production patches: `0`

Permanent machine-readable evidence is stored at:

`evidence/batch-pilot-known-archetypes/2026-08-02/seattle-public-schools.json`
