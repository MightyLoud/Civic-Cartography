# Separate generation completeness from validation enrichment

## Problem

The real upstream capture used the upstream pipeline response status as a proxy
for generation completeness. A target was reported as `partial` whenever the
upstream response was `partial`, even when both required artifacts had been
written and the expected Jurisdiction classification was present.

That conflated two different questions:

1. Did the generator produce complete Division and Jurisdiction artifacts?
2. Did the artifacts receive full validation-data enrichment?

After upstream fixes 1 and 2, Pierce County and Colorado Springs School District
11 answer yes to the first question and no to the second. The acceptance report
must preserve both facts.

## Decision

The capture acceptance normalizer applies these rules:

- `generation_status=generated` when every selected upstream candidate produced
  both a Division path and a Jurisdiction path.
- Upstream response status is retained in diagnostics as `enrichment_status`:
  `complete`, `partial`, `failed`, or `not_run`.
- Partial enrichment does not negate complete artifact generation.
- Failed enrichment remains a blocking exception even when artifact paths exist.
- Alias groups remain blocked until exactly one canonical Jurisdiction artifact
  is selected.
- Missing artifacts remain partial or failed generation.

Raw upstream attempts are not rewritten. The normalizer only updates the
execution overlay consumed by the target-manifest report and adds explicit
acceptance metadata to the diagnostics file.

## Operational change

The main six-fixture workflow now applies the two already validated upstream
patches before capture:

1. continue jurisdiction classification after stub Division generation;
2. normalize blank and null-like LSAD values.

It then normalizes capture acceptance semantics before building each report.

## Confirmed result

The two pinned captures produced identical reports with run ID
`cc9fa7a98a3d22e8cc21`. Evaluation `63323d36b8a7d07eb265` confirmed:

- **4/6 fixtures passed**;
- **6/6 fixtures were deterministic**;
- full report content matched;
- median recorded review time was `0.0` minutes.

| Fixture | Generation | Enrichment | Result |
|---|---|---|---|
| Seattle | generated | complete | passed |
| Tacoma | generated | complete | passed |
| Pierce County | generated | partial | passed |
| Colorado Springs School District 11 | generated | partial | passed |
| Regional Transportation District | skipped | not run | failed: `upstream_target_not_found` |
| City and County of Denver | generated | partial | failed: `upstream_alias_noncanonical` |

Pierce County and District 11 now pass without hiding their missing validation
enrichment. RTD remains unresolved, and Denver remains blocked because two
Jurisdiction artifacts exist where one canonical Jurisdiction is required.

## Permanent evidence

- `evidence/upstream-fix-3/2026-08-02/source-manifest.json`
- `evidence/upstream-fix-3/2026-08-02/fixture-evaluation.json`
- `evidence/upstream-fix-3/2026-08-02/enrichment-summary.json`

This change does not solve RTD selection or Denver canonicalization, and it does
not hide either failure.
