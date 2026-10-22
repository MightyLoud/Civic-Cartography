# Olmos Park Census provenance reconciliation — draft proposal

Based on #491 tree `fc44211ba20a2d7b41b1d6a28d4dfc0c3975e5e7`.

Fresh October 22 Census TIGERweb evidence for incorporated-place GEOID 4853988 has exactly identical coordinates and stable source values to the prior snapshot. The proposal updates verified source vintage from 2025-01-01 to 2026-01-01, capture date from August 1 to October 22, and raw integer representation and volatile service bookkeeping. No coordinate tolerance or simplification was used.

Original raw and canonical bytes are preserved exactly under `data/raw/olmos-park/archive/2026-08-01/`. Only the Census row in the existing manifest and the Olmos Park fetch date in the shared workflow are updated. Officeholder and election evidence, normalized records, other jurisdictions, workflow triggers, permissions and comparison gates remain intact. This does not recertify the current municipal roster or election facts.

Local validation: 254 tests passed; 33 normalized files passed; GeoJSON joins and fresh Census raw/canonical comparisons passed. A regression check enforces archive support, exact geometry, stable values and matching manifest attribution. All archived bytes match the parent tree.

This is a draft proposal, not merged. Combined GitHub CI is unverified. Passing the Olmos Park comparison will allow the shared workflow to reach subsequent independent checks; it does not establish that those checks pass. Production promotion and merging require separate approval. No workflow was manually dispatched.

Rollback restores the archived raw/canonical pair and the prior Census manifest vintage/date and Olmos Park workflow capture date together.
