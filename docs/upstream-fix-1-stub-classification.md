# Upstream fix 1: continue classification after stub Division generation

## Status

Validated against:

`openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`

The connected GitHub integration has read-only access to the upstream
repository. Creating the required upstream issue returned `403`, so the patch
must not be submitted upstream until an issue is opened by a contributor with
permission.

Tracking issue: `MightyLoud/Civic-Cartography#43`.

## Baseline failure

The original real two-run baseline produced:

- Seattle: Division and Jurisdiction
- Tacoma: Division and Jurisdiction
- Pierce County: stub Division only
- Colorado Springs School District 11: stub Division only
- RTD: unresolved
- Denver: place Division/Jurisdiction plus county stub Division

The no-validation-match branch returned immediately after the stub Division was
written. The existing reusable OCDID classifier was never called.

## Patch behavior

The patch:

1. extracts the existing Jurisdiction-generation block into a private helper;
2. calls that helper after a no-match stub Division is written;
3. passes `lsad_code=None` for a stub because no validation LSAD exists;
4. preserves the quarantine record and `partial` response status;
5. leaves ambiguous multiple-match records unchanged; and
6. adds focused unit tests outside `tests/integration` and `tests/sample_output`.

The successful-match path uses the same helper but passes its existing LSAD
value unchanged. Global blank-LSAD normalization remains separate.

## Confirmed result

The final validation workflow passed every infrastructure and behavior check:

- ordinary `git apply --check` succeeded;
- the regenerated Git diff matched the committed patch byte-for-byte;
- the new upstream unit tests passed;
- Ruff passed for both changed Python files;
- two clean patched captures completed;
- all six fixtures remained deterministic; and
- both complete reports were identical.

Measured fixture impact:

| Fixture | Before | After fix 1 |
|---|---|---|
| Seattle | generated `government` | unchanged |
| Tacoma | generated `government` | unchanged |
| Pierce County | stub Division only | Division plus `government` Jurisdiction |
| Colorado Springs School District 11 | stub Division only | Division plus `school_system` Jurisdiction |
| Regional Transportation District | unresolved | unchanged |
| City and County of Denver | place complete; county stub only | both alias members produce `government` Jurisdictions |

Evaluation ID: `4a351bffd71563a15f53`  
Both run IDs: `d6293fee3205c7f2669f`

Permanent evidence:

- `evidence/upstream-fix-1/2026-08-02/source-manifest.json`
- `evidence/upstream-fix-1/2026-08-02/fixture-evaluation.json`

## Why the strict gate remains 2/6

Fix 1 intentionally preserves `Status.PARTIAL` when validation enrichment is
missing. Pierce County, District 11, and Denver now classify and generate
Jurisdictions correctly, but the acceptance adapter still records their runs as
partial with an explicit review reason.

That is not a failure of fix 1. It keeps missing enrichment visible rather than
claiming full generation. RTD selection and canonical consolidated-alias output
remain separate reusable changes.
