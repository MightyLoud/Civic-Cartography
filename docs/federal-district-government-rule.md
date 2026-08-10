# Federal district root government classification

## Evidence

The fail-closed MB100-075 probe on PR #288 matched
`ocd-division/country:us/district:dc` from the retained national master and
routed its stub Division to `divisions/dc/local`. Run `31346919106` retained
RAW input, identifier join, source provenance, and deterministic parity, but
failed the completion contract because no Jurisdiction artifact was generated.

The pinned upstream classifier removes `district` from the set of leaf division
types. An admin-1-only federal-district OCDID therefore resolves to division type
`unknown`, even though the District of Columbia is a governing jurisdiction.

## Decision

Classify only a U.S. admin-1 root whose OCDID contains `district:` and no leaf
segment below it as a general government Jurisdiction. Keep ordinary children,
including Advisory Neighborhood Commissions, on the existing leaf-type path.

This is a reusable generator rule, not a target-specific override. Existing
state, territory, municipality, county, school, transit, alias, and special-
district behavior remains unchanged.

## Acceptance

- patches 0001 through 0007 apply cleanly to the pinned upstream revision
- `district:dc` classifies as `government`
- `district:dc/anc:...` remains governed by the existing ANC rule
- a no-validation-match D.C. stub can create
  `ocd-jurisdiction/country:us/district:dc/government`
- focused upstream tests and Ruff pass
- MB100-075 is rerun from merged production before workbook completion advances
