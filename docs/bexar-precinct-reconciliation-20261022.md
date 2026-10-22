# Bexar precinct snapshot reconciliation — draft review

Based on draft #497. Two official October 22 captures are byte-identical. District 1 is unchanged. Districts 2, 3 and 4 have respectively 6, 11 and 7 changed coordinate scalars, maximum absolute delta 2.1316282072803006e-14 degrees. Every changed value is enumerated in coordinate-changes.json. Stable source attributes and vertex counts match; original and fresh polygons are valid. These are numerical diagnostics, not evidence of physical boundary movement. Cause remains unverified.

This proposal archives original raw/canonical precinct bytes, adopts the exact official capture, and updates only precinct manifest/replay attribution. Census data, roster and consolidation contracts, identifiers and strict comparators are retained. No rounding, tolerance or future comparison exception is introduced.

User approved draft upload including the 24 coordinate changes; not approved for merge or production. No merge, production promotion, manual workflow dispatch or governance closure. Rollback restores original precinct snapshots and prior precinct attribution together. GitHub workflow verification remains pending.
