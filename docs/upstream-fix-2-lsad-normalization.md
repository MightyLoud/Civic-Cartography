# Upstream fix 2: normalize blank LSAD values

## Status

This work prepares and validates a second patch against:

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

## Validation contract

The dedicated workflow applies fix 1 and fix 2 to the pinned upstream revision,
then proves:

- targeted upstream tests pass;
- Ruff passes;
- blank and null-like values classify by OCDID type;
- a real unknown code remains an error;
- the two real six-fixture captures remain identical; and
- no fix-1 Jurisdiction output regresses.

Fix 2 is a classifier correctness change. It is not expected to increase the
strict six-fixture pass count because the current failed fixtures are still
explicit partial-enrichment, RTD-selection, and alias-canonicalization cases.
