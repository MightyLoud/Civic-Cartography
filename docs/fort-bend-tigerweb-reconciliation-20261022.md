# Fort Bend Census source-value reconciliation — draft proposal

Based on #494 tree `573c083385d04b100f137e6c64521bbd338faef6`.

Fresh October 22 Census county GEOID 48157 preserves exact coordinates. AREALAND changes from 2,232,877,080 to 2,232,877,078 square metres (-2); AREAWATER changes from 60,631,457 to 60,631,454 (-3). Combined reported area decreases by 5 square metres. All other stable source values match. The cause remains unverified; no boundary change, rounding explanation or reclassification cause is inferred.

The candidate archives the original raw/canonical bytes exactly and adopts fresh Census source values, verified 2026 vintage and October 22 attribution. Only the Census manifest row and countywide replay date change. Commissioner snapshots and replay dates, current/archive divergence contracts, roster evidence, normalized records, identifiers and strict comparison gates remain intact. No coordinate tolerance or area-value exception is introduced.

The regression requires exact geometry, pins old/new land and water values, compares every other stable value, validates archived/current raw-canonical support and checks manifest attribution. Future source-value drift still fails the existing live comparison.

Local validation is recorded in verification.json. Full GitHub workflow and live Commissioner comparisons remain unverified for this candidate. This does not recertify officeholders or explain the area changes.

Status: draft proposal, not merged or approved for production. These numeric changes were approved for draft review; merge and production promotion require separate approval. No manual workflow dispatch, release activation or governance closure occurred. Rollback restores archived files and the prior Census manifest/workflow date together.
