# El Paso Census provenance repair — draft candidate

The October 22 Census capture for GEOID 48141 has exactly identical coordinates and stable source values to the archived August 2 snapshot. Area values are now JSON integers instead of equivalent digit strings; the current layer reports January 1, 2026 vintage. This candidate updates only Census raw/canonical attribution and representation, its existing manifest row, and the Census workflow replay date. Commissioner evidence dates and polygons remain unchanged.

Original raw and canonical bytes are archived under `data/raw/el-paso-county/archive/2026-08-02/` and verified against the base Git commit. A regression test checks identical coordinates and stable values, both raw/canonical pairs, and matching manifest attribution. Verification hashes are in `evidence/el-paso-tigerweb-reconciliation-20261022/verification.json`.

Validation: 231 repository tests passed; normalized validation passed for 34 files; GeoJSON joins passed; raw/canonical support and archive byte equality passed. No tolerances, rounding, simplification or geometry repair were applied.

This candidate is based on unmerged PR #481's corrected generator/comparator. Complete El Paso CI also needs PR #487's portal correction and its dependency stack. The candidate is proposed for review and remains unmerged; combined GitHub CI is unverified. No production baseline replacement or release is approved. This Census provenance refresh does not recertify officeholders or establish legal boundary authority.
