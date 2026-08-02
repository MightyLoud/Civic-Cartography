# Upstream fix 1: continue classification after stub Division generation

## Status

This work prepares and validates a patch against:

`openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`

The connected GitHub integration has read-only access to the upstream
repository. Creating the required upstream issue returned `403`, so the patch
must not be submitted upstream until an issue is opened by a contributor with
permission.

Tracking issue: `MightyLoud/Civic-Cartography#43`.

## Baseline failure

The real two-run baseline produced:

- Seattle: Division and Jurisdiction
- Tacoma: Division and Jurisdiction
- Pierce County: stub Division only
- Colorado Springs School District 11: stub Division only
- RTD: unresolved
- Denver: place Division/Jurisdiction plus county stub Division

The no-validation-match branch returns immediately after the stub Division is
written. The existing reusable OCDID classifier is never called.

## Patch behavior

The patch:

1. extracts the existing Jurisdiction-generation block into a private helper;
2. calls that helper after a no-match stub Division is written;
3. passes `lsad_code=None` for a stub because no validation LSAD exists;
4. preserves the quarantine record and `partial` response status;
5. leaves ambiguous multiple-match records unchanged; and
6. adds focused unit tests outside `tests/integration` and `tests/sample_output`.

The successful-match path uses the same helper but passes its existing LSAD
value unchanged. Global blank-LSAD normalization remains fix 2.

## Validation contract

The dedicated workflow must prove:

- the patch applies cleanly to the pinned upstream commit;
- its new upstream unit tests pass;
- upstream Ruff checks pass for the changed Python files;
- Pierce County produces a `government` Jurisdiction path;
- Colorado Springs School District 11 produces a `school_system` Jurisdiction
  path;
- Denver's county alias member also reaches Jurisdiction generation;
- both complete captures remain identical; and
- all six fixtures remain deterministic.

The strict six-fixture gate may remain red because fix 1 intentionally preserves
the upstream `partial` status and does not solve RTD selection or canonical
alias handling.
