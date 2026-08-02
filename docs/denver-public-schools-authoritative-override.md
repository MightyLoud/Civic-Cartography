# Denver Public Schools authoritative override

## Decision

`BP25-015` resolves through a maintained authoritative override for **Denver County School District 1**, publicly known as **Denver Public Schools**.

The unchanged manifest selector is:

```text
School District No. 1 in the City and County of Denver
```

The maintained exact aliases are:

- Denver County School District 1
- Denver County 1
- Denver Public Schools
- School District No. 1 in the City and County of Denver

No fuzzy matching is used.

## Authoritative identity

Colorado Department of Education identifies the district as **Denver County 1**, district code **0880**.

The U.S. Census Bureau identifies the unified school district as **Denver County School District 1**, GEOID **0803360**.

The district's public-facing name and website are **Denver Public Schools** and `https://www.dpsk12.org/`.

## Maintained OCDID

```text
ocd-division/country:us/state:co/county:denver/school_district:denver_county_school_district_1
```

This follows the county-nested `school_district` structure already validated by the Colorado Springs School District 11 fixture.

## Why an override is required

The current Colorado local OCD-ID input contains no matching Denver school-system row. This is therefore a maintained source-gap override, not a classification patch or a target-specific change to generator logic.

## Confirmed generation result

- match status: `matched`
- inferred classification: `school_system`
- classification status: `matched`
- generation status: `generated`
- exception class: none
- review reason: none

Generated files:

```text
divisions/co/local/denver_county_school_district_1__bf587c6e-3faf-53cd-9095-b2bbbf7d7d31.yaml
jurisdictions/co/local/denver_county_school_district_1_7fdc49bd-a8ec-5be4-991c-87e149e9198d.yaml
```

## Batch Pilot effect

- known-archetype classification: **14/15 (93.3%)**
- known-archetype generation: **14/15 (93.3%)**
- regression fixtures: **6/6 passed**
- deterministic targets: **25/25**
- reports identical: **true**
- target-only production patches: **0**

## Evidence

- target evidence: `evidence/batch-pilot-known-archetypes/2026-08-02/denver-public-schools.json`
- workflow run: `30772205379`
- artifact ID: `8840916820`
- artifact digest: `sha256:cdcbcf8edcc37224c3086e1b2e4aedb855cce99eb20e84677cc3ffb026d8ea11`
