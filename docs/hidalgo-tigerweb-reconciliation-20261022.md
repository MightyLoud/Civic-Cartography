# Hidalgo Census source-value reconciliation — draft review

Based on #495 tree `4c63d7416838b9e50c140252121a01982174aacc`.

Fresh October 22 Census county GEOID 48215 preserves exact coordinates. AREALAND changes from 4,069,433,009 to 4,069,433,006 square metres (-3). AREAWATER and every other stable source value are unchanged. The cause remains unverified; no annexation, rounding or land/water reclassification explanation is inferred.

This nine-file candidate archives prior raw/canonical bytes exactly, adopts fresh Census values and verified 2026 vintage/October 22 attribution, and updates only the Census manifest row and countywide replay date. Commissioner snapshots/dates, dual-body/adoption contracts, roster evidence, normalized records, identifiers, triggers, permissions and strict comparison gates remain intact. No geometric tolerance or area-value exception is introduced.

The regression pins both old/new land values and unchanged water, requires exact geometry and equality of every other stable value, validates archived/current raw-canonical support and checks manifest attribution. Local validation results are retained in verification.json. Live Commissioner comparisons and full GitHub workflow execution remain unverified for this candidate.

Status: approved for upload as a draft PR, not merged or approved for production. The user explicitly approved the numeric land-area change for draft review. No manual dispatch, release activation or governance closure occurred. Rollback restores archived files and the prior Census manifest/workflow date together.
