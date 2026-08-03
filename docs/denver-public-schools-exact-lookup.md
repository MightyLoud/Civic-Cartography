# Denver Public Schools exact lookup

## Decision

Batch Pilot target `BP25-015` keeps the human-facing jurisdiction name **Denver Public Schools** and uses the exact upstream selector name **School District No. 1**.

This is a maintained exact-name lookup. It is not fuzzy matching.

## Root cause

The previous selector used a longer legal-style name:

`School District No. 1 in the City and County of Denver`

The pinned Open Civic Data master source instead contains:

- OCDID: `ocd-division/country:us/state:co/county:denver/school_district:school_district_no._1`
- source name: `school district no. 1`
- federal district identifier: `0803360`

The source label is unique in the pinned national master used by the Batch Pilot run.

## Implementation

The manifest selector is:

```yaml
- target_id: BP25-015
  jurisdiction_name: Denver Public Schools
  state: co
  selector:
    type: explicit_lookup
    name: School District No. 1
    resolution_policy: override_or_exception
  expected_classification: school_system
```

The resolver normalizes punctuation and capitalization, then requires an exact maintained-name match. Multiple matches remain an explicit ambiguity failure.

No generator patch, fuzzy matching rule, or authoritative override was added.

## Confirmed output

The two-run Batch Pilot workflow generated:

- Division: `divisions/co/local/school_district_no._1__6a306d74-9af3-5e1e-b315-16fd41a7b53f.yaml`
- Jurisdiction: `jurisdictions/co/local/school_district_no._1_6c138fd0-81cd-5a13-8bb3-e9b1075c985a.yaml`
- Jurisdiction OCDID: `ocd-jurisdiction/country:us/state:co/county:denver/school_district:school_district_no._1/school_system`
- classification: `school_system`

The target has no exception class and no review reason. Source enrichment remains partial because the validation sheet did not contain a matching enrichment row; this does not block Division or Jurisdiction generation.

## Batch result

- known-archetype classification: `14/15` (`93.3%`)
- known-archetype generation: `14/15` (`93.3%`)
- regression fixtures: `6/6`
- deterministic targets: `25/25`
- reports identical: `true`
- target-only production patches: `0`

Permanent machine-readable evidence is stored at:

`evidence/batch-pilot-known-archetypes/2026-08-02/denver-public-schools.json`
