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

## Expected gate movement

The expected honest result is **4/6**:

- Seattle: pass
- Tacoma: pass
- Pierce County: pass with partial enrichment recorded in diagnostics
- Colorado Springs School District 11: pass with partial enrichment recorded
- Regional Transportation District: fail because no authoritative target is resolved
- City and County of Denver: fail because two Jurisdictions are generated and
  one canonical Jurisdiction has not yet been selected

This change does not solve RTD selection or Denver canonicalization, and it must
not hide either failure.
