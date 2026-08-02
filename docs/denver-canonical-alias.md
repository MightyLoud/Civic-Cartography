# Canonicalize the City and County of Denver alias group

## Problem

The upstream identifier inputs contain two valid geographic Divisions for the
same consolidated government:

- `ocd-division/country:us/state:co/place:denver`
- `ocd-division/country:us/state:co/county:denver`

After the stub-classification fixes, both Divisions independently generate a
`government` Jurisdiction. The artifacts are individually valid, but the target
manifest requires one result for the City and County of Denver. Two generated
Jurisdictions therefore remain an explicit `upstream_alias_noncanonical`
failure.

## Evidence basis

Official Denver materials consistently identify the governing entity as the
**City and County of Denver**. The U.S. Census Bureau records Denver County as
coextensive with Denver city. The two identifiers represent distinct geography
labels, not two independently governed local governments.

Maintained source URLs:

- City and County of Denver: <https://www.denvergov.org/>
- U.S. Census Bureau county-change documentation: <https://www.census.gov/programs-surveys/geography/technical-documentation/county-changes.1980.html>
- Colorado Constitution: <https://leg.colorado.gov/laws/colorado-constitution>

## Decision

Add a maintained canonical-alias registry with an exact member-set match.
The Denver entry selects the place Division as the canonical representative:

`ocd-division/country:us/state:co/place:denver`

The resulting shared Jurisdiction ID is:

`ocd-jurisdiction/country:us/state:co/place:denver/government`

The choice is explicit rather than inferred. The place member is used because
the unified government is officially styled the City and County of Denver and
the manifest lists the incorporated-place member first. Future consolidated
entities may select a different canonical member through their own reviewed
registry entry.

## Generation behavior

For every maintained alias group:

1. Preserve and generate every Division member.
2. Set every Division's `jurisdiction_id` to the maintained canonical
   Jurisdiction ID.
3. Generate the Jurisdiction only for the canonical member.
4. Explicitly suppress duplicate Jurisdiction generation for secondary members.
5. Retain enrichment status separately for each upstream attempt.

The capture adapter records canonical-alias metadata in diagnostics. Acceptance
passes only when all of these invariants are proven:

- the exact maintained member set was selected;
- every member produced one Division artifact;
- exactly one canonical member produced a Jurisdiction artifact;
- every secondary member produced no Jurisdiction artifact and records explicit
  suppression;
- every member points to the same canonical Jurisdiction ID; and
- the canonical Jurisdiction matches the expected classification.

## Non-goals

- Do not delete or merge the two Denver Division records.
- Do not use fuzzy matching to discover alias groups.
- Do not choose a canonical member based on sort order at runtime.
- Do not hide enrichment failures.
- Do not generalize one Denver-specific output patch; add reusable registry and
  generator behavior instead.

## Expected result

The six-fixture gate should move from **5/6** to **6/6** while remaining fully
deterministic. The City and County of Denver should report two Division paths,
one canonical government Jurisdiction path, and no exception.
