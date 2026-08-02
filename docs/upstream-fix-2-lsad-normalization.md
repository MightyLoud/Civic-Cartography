# Upstream fix 2: normalize blank LSAD values

## Status

Validated against:

`openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`

Patch 2 is applied after the validated stub-classification patch from fix 1.
The connected GitHub integration remains read-only for the upstream repository,
so the patch cannot be submitted upstream until an issue is opened by a
contributor with permission.

Tracking issue: `MightyLoud/Civic-Cartography#43`.

## Problem

The Division generator already normalizes LSAD cells through
`coerce_lsad_code()`, but `infer_jurisdiction_seed()` accepts raw LSAD text and
passes it directly to strict lookup. Empty strings and null-like CSV strings can
therefore raise as unknown codes before OCDID type rules run.

## Fix

The patch reuses `coerce_lsad_code()` at the classifier boundary and converts an
empty normalized value to `None`.

This means:

- `None`, `""`, whitespace, `"None"`, and `"null"` are treated as absent;
- county and school-district OCDID rules can classify normally;
- list-repr cells retain the existing first-code behavior;
- known LSAD codes retain their current semantics; and
- unknown nonblank values still raise.

## Validation result

The dedicated workflow proved:

- ordinary `git apply --check` for fix 1 and standalone fix 2;
- regenerated fix-2 diff matches the committed patch byte-for-byte;
- targeted upstream tests pass;
- Ruff passes;
- blank and null-like values classify by OCDID type;
- a real unknown code remains an error;
- both real six-fixture captures are identical;
- all six fixtures remain deterministic; and
- no fix-1 Jurisdiction output regresses.

Evaluation ID: `4a351bffd71563a15f53`  
Both run IDs: `d6293fee3205c7f2669f`

## Fixture impact

The strict gate remains **2/6**, as expected. Fix 2 is a classifier correctness
change; the remaining failures are explicit partial-enrichment semantics, RTD
selection, and consolidated-alias canonicalization.

## Permanent evidence

- `evidence/upstream-fix-2/2026-08-02/source-manifest.json`
- `evidence/upstream-fix-2/2026-08-02/fixture-evaluation.json`
