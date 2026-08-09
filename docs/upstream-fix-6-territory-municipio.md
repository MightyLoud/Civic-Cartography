# Territory and municipio capture support

## Problem

The batch adapter treated every two-letter U.S. postal code as an OCDID
`state:` segment and downloaded `state-{code}-local_gov.csv`. Puerto Rico uses
`territory:pr`, and the upstream identifier repository has no
`state-pr-local_gov.csv`. The same state-only assumption also existed in target
validation, generator matching, classification, and artifact output routing.

## Reusable boundary

- Target manifests accept `state:`, `district:`, and `territory:` admin-1
  segments while still requiring the segment code to match `target.state`.
- State targets keep the existing national-master plus state-local cross-check.
- District and territory targets resolve exact selectors from the retained
  national master instead of inventing a state-local URL.
- National-master metadata is preserved on the ingest record so its Census
  GEOID can select the normalized validation row deterministically.
- The pinned upstream generator recognizes `territory` + `municipio`, classifies
  municipios as general government, and writes leaf and ancestor artifacts
  under the postal-code directory (`pr/`).

## Regression proof

Focused Civic-Cartography tests cover manifest validation, source routing, and
national-master candidate retention. The upstream patch carries four tests for
GEOID matching, municipio classification, leaf output routing, and territory
ancestor routing.

A two-run isolated local integration fixture for San Juan produced identical
reports, diagnostics, execution results, and artifact SHA-256 values. Both runs
reported `matched`, `generated`, classification `matched`, and no exception.

The production MB100-050 workflow remains the authority for completion. Its two
clean captures, full source inputs, completion contract, register projection,
and strict San Juan identity checks must all pass before tracker movement.
