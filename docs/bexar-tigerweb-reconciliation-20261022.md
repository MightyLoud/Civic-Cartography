# Bexar Census source-value reconciliation — draft review

Based on #496 tree 64ce9aa962facfb7240790eb43976441f4b02262.

Fresh October 22 Census GEOID 48029 preserves exact coordinates. AREALAND changes from 3,212,765,009 to 3,212,765,014 square metres (+5). AREAWATER remains 40,484,944 and every other stable source value matches. The cause is unverified; no legal boundary change or rounding explanation is inferred.

Original August 2 raw/canonical bytes are archived exactly. Fresh Census capture carries verified 2026 vintage and October 22 attribution. Only the Census manifest row and countywide workflow replay date change. Precinct sources/dates, roster and consolidation contracts, normalized records, identifiers and strict comparators remain intact. No tolerance or area exception is introduced.

The regression pins old/new land and unchanged water, exact geometry, all other stable values, archived/current raw-canonical support and manifest attribution. Live precinct comparisons and GitHub CI remain unverified for this candidate.

Status: user approved draft upload including the land-value change; not merged or approved for production. No merge, production promotion, manual dispatch or governance closure. Rollback restores archives and prior Census manifest/workflow date together.
