# Arlington Census provenance reconciliation — draft proposal

Based on #492 tree `9bc77e5ab603c64082cc6ce3f95b650c898bb563`.

Fresh October 22 Census evidence for GEOID 4804000 preserves exactly identical coordinates and stable source values. The candidate refreshes verified 2026 vintage and capture attribution, integer AREA representation and volatile service bookkeeping. Original raw/canonical bytes are archived exactly under data/raw/arlington/archive/2026-08-01/.

Only the Census manifest row and Arlington citywide replay date change. Council-district snapshots, their retrieval dates, officeholder and election evidence, normalized records, identifiers and strict comparison gates remain unchanged. No coordinate tolerance or simplification was used.

Local validation: 255 tests passed, 33 normalized files passed, GeoJSON joins passed, fresh Census comparison passed, archived bytes match parent. The added regression verifies exact geometry, stable values, raw/canonical support and manifest attribution. Live council-district source comparisons and combined GitHub CI have not yet been run for this candidate; no full-workflow success is claimed.

This proposal remains draft, not merged or approved for production. Addison's independent source reconciliation blocker remains open. No manual dispatch or release activation occurred. Rollback restores archived countywide files and the prior Census manifest/workflow date together.
