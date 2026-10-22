# Galveston Census provenance reconciliation — draft

This is one bounded proposal based on PR #481's corrected generator/comparator. It does not approve a production release or change the county polygon's coordinates.

## Verified change

A fresh read of Census TIGERweb county GEOID `48167` on October 14, 2026 produced exactly the same geometry and stable source values as the approved snapshot. Changes are limited to:

- reported layer vintage: `2025-01-01` → verified `2026-01-01`;
- Census capture date: `2026-08-02` → `2026-10-14`;
- raw `AREALAND` and `AREAWATER`: digit strings → equal JSON integers; and
- the service's volatile `OBJECTID`: `2809` → `2891`.

The exact geometry SHA-256, using sorted compact JSON serialization, is `9ffd6cc930a627af79a87275fd45711bba606ea02b08829579002a77f3814441` for both snapshots. No geometric tolerance, simplification or coordinate normalization was used.

The prior raw and canonical files are preserved byte for byte in `data/raw/galveston-county/archive/2026-08-02/`. The active raw/canonical pair is updated only on this draft branch. The Census row in the existing 18-source manifest records the current capture. The existing Galveston workflow's Census replay date is updated to match; its triggers, permissions and gates remain intact. Commissioner-precinct replay attribution stays unchanged.

Normalized rows, officeholder evidence, abolished-office evidence, Commissioner polygons and portal contracts are unchanged. Their prior retrieval dates remain intact; this is not a new certification of the entire elected roster. PR #480's manual preflight is untouched and `GATE-CM-006` remains `WAIT`.

## Validation

- 36 focused Galveston/TIGERweb tests passed.
- Full local suite: 231 passed.
- Normalized validation: 34 files passed.
- GeoJSON joins: passed.
- Fresh Census raw/canonical and committed/fresh comparisons: passed.
- Fresh four-precinct ArcGIS snapshot comparison: passed.
- Existing roster, abolished-office, enrolled-law, cutover, Experience, legacy-item and operational-layer contracts: passed under the existing source-access policy.
- Archived raw and canonical bytes: identical to their parent-commit versions.
- Current county coordinates and stable source values: identical to archived evidence.

Twelve optional county web pages returned HTTP 403; one county source page was accessible. The validator preserved its existing committed-evidence fallback and mandatory enrolled-law/ArcGIS checks. Do not present this as fresh online confirmation of every officeholder.

The [verification record](../evidence/galveston-tigerweb-reconciliation-20261014/verification.json) contains exact hashes and the validation scope. GitHub exact-head results must be read back after this draft is created. Repository-wide CI will still contain unrelated TIGERweb, El Paso and LIC-G5 blockers; this proposal does not clear them.

## Approval and rollback

Status: prepared draft, not merged. The main-branch baseline remains unchanged. No manual workflow dispatch, release or monitoring activation was performed.

The reviewer should confirm the exact-coordinate/source-value equality, archived evidence, Census attribution, and Galveston exact-head validation. Merge approval remains separate, including the dependency on PR #481. If this proposal is declined, retain the existing main baseline. If a subsequently approved merge needs reversal, revert this bounded commit and restore the archived raw/canonical pair and prior Census manifest/workflow dates together.
