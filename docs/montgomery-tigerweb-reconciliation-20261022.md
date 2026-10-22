# Montgomery Census source-value reconciliation — draft proposal

Based on #493 tree `6320b01534d30e9b96f7f6dd1fdea175a14d9080`.

Fresh October 22 Census county GEOID 48339 preserves exact coordinates. AREALAND changes from 2,699,229,345 to 2,699,231,373 square metres (+2,028). AREAWATER changes from 89,891,730 to 89,889,706 square metres (-2,024). Combined reported area changes by +4 square metres. All other stable source attributes match. These numeric changes are substantive Census source values; their cause remains unverified. No annexation or reclassification cause is inferred.

This bounded candidate archives prior raw/canonical bytes exactly, adopts the freshly reported Census values with verified 2026 vintage and October 22 capture attribution, and updates only the Census manifest row and countywide workflow replay date. Commissioner geometry/dates, roster evidence, normalized records, identifiers, workflow permissions and strict comparison gates remain unchanged. No geometric tolerance or area-value exception is added to the comparator.

The regression test pins both old and proposed area values, requires exact coordinate equality and equality of every other stable source value, validates archived/current raw-to-canonical support and matching manifest attribution. Future live area changes will continue to fail the existing strict comparison.

Local validation results are recorded in the verification JSON. Live Commissioner comparisons and full GitHub workflow execution remain unverified for this candidate. This is not a new certification of every roster or portal source.

Status: draft candidate; not merged or approved for production. The numeric-area changes were approved for draft review; merge and production promotion require separate approval. No manual dispatch, release activation or governance closure occurred. Rollback restores archived files and the prior Census manifest/workflow date together.
