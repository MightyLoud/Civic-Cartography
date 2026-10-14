# TIGERweb validation investigation — October 14, 2026

## Finding

The failures associated with [draft PR #480](https://github.com/MightyLoud/Civic-Cartography/pull/480) are not evidence that its manual HTTPS preflight broke geography generation. The PR changes only its new manual workflow and documentation. Its base and the current `main` are `fcde296ed74c588c44046d8575ab58c00ca623a0`; its head is `ae7cae705c658f718af6d02e3b3bf2c47132e393`.

All 21 associated pull-request workflow runs were inspected. Irving passed; 18 stopped at a TIGERweb canonical snapshot comparison; El Paso stopped at its portal-layer contract; LIC-G5 failed its lock comparison. Later checks skipped after each failed step must not be treated as passes.

The same base commit already failed the Travis boundary comparison in [run 38570741341](https://github.com/MightyLoud/Civic-Cartography/actions/runs/38570741341), at 13:19 UTC on October 14, before PR #480 was created at 13:21 UTC. Travis, Denton and El Paso also have failed runs of that same base on September 25. Their August 22 `main` runs passed. The generator and comparison implementations have not changed in PR #480.

## Live source comparison

Read-only requests to the exact source URLs stored in the committed canonical files were repeated on October 14. All 18 stored raw snapshots regenerate their committed canonical features successfully when supplied their recorded identifiers, vintage and retrieval label. This rules out a baseline regeneration defect in the inspected generators.

The [Current service](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer?f=pjson) describes itself as January 1, 2026 vintage. The [county layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/82?f=pjson), [incorporated-place layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/28?f=pjson) and [unified-school-district layer](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/14?f=pjson) agree. The repository snapshots carry `source_vintage=2025-01-01`.

After removing only existing service bookkeeping fields and treating equal integer `AREALAND`/`AREAWATER` strings and numbers as equivalent:

| Boundary checked | Coordinate change | Actual source-value changes |
| --- | --- | --- |
| Travis County | Yes | AREALAND, AREAWATER |
| Denton County | Yes | AREALAND, AREAWATER, CENTLAT, CENTLON |
| Carrollton-Farmers Branch ISD | Yes | AREALAND, CENTLAT, CENTLON |
| Oak Point | Yes | AREALAND, AREAWATER, CENTLAT, CENTLON, INTPTLAT, INTPTLON |
| Tarrant County | Yes | AREALAND, AREAWATER, CENTLAT, CENTLON |
| Williamson County | Yes | AREALAND, AREAWATER |
| Harris County | Yes | AREALAND, AREAWATER |
| Dallas County | Yes | AREALAND, AREAWATER, CENTLAT, CENTLON |
| Collin County | Yes | AREALAND, AREAWATER, CENTLAT |
| Montgomery County | No | AREALAND, AREAWATER |
| Fort Bend County | No | AREALAND, AREAWATER |
| Hidalgo County | No | AREALAND |
| Bexar County | No | AREALAND |
| Kerr County | No | AREALAND, AREAWATER |
| Galveston County | No | None; integer representation only |
| Kaufman County | No | None; integer representation only |
| Arlington | No | None; integer representation only |
| Olmos Park | No | None; integer representation only |

Thus 9 snapshots have coordinate changes, 5 have source-value changes with identical coordinates, and 4 have only integer representation changes in the source view. This classification does not approve any replacement geometry or establish a legal boundary change.

Examples of substantive source changes, in square metres:

| County | Field | Stored value | Fresh value |
| --- | --- | ---: | ---: |
| Travis | AREALAND | 2,575,299,585 | 2,575,354,868 |
| Travis | AREAWATER | 79,506,870 | 79,451,592 |
| Denton | AREALAND | 2,275,331,242 | 2,274,391,019 |
| Denton | AREAWATER | 189,459,989 | 190,747,364 |

Second Current fetches for Travis, Denton, Olmos Park and CFBISD returned the same stable source attributes and coordinates as the initial fetches. Identical stored raw evidence regenerates identically. The observed discrepancies are not explained by nondeterministic local generation.

The equivalent queries against `tigerWMS_ACS2025` were also checked for all 18 boundaries. Those current responses match the Current responses in the stable source view, and still differ from the stored evidence as shown above. Therefore switching to the named 2025 endpoint would not reproduce these baselines. A moving service's historical vintage label is not an immutable content pin. The exact upstream edit date and whether edits represent legal changes or Census corrections remain unverified.

## Focused correction

The code correction makes no baseline or workflow changes:

1. Fetch the official layer vintage before and after a source query. Missing or unrecognized metadata, invalid dates and a vintage rollover fail before output files are written. All three generators require the verified vintage when canonicalizing instead of hard-coding 2025.
2. Normalize only digit strings in `AREALAND` and `AREAWATER` to exact integers in comparison copies. Preserve raw evidence and canonical files. A one-square-metre value change still fails; GEOID, names, join identifiers, attribution, vintage and coordinates remain significant.
3. Report coordinate, source-attribute and canonical-property differences separately, with field names rather than a generic mismatch alone.

Accurate 2026 provenance still differs from the approved 2025 baseline label, even for the four boundaries with unchanged stable source content. Those full comparisons remain blocked. This change must not be represented as making all geography CI green.

The existing `--retrieved-at` workflow values remain release replay labels. No attempt is made here to silently revise historical retrieval records. The metadata guard detects vintage rollover, not every possible within-vintage upstream edit; exact snapshot comparison remains the safeguard for content changes.

## Separate failures

### El Paso portal source migration

[Run 38577371017](https://github.com/MightyLoud/Civic-Cartography/actions/runs/38577371017) fails before TIGERweb fetching. The implementation expects `https://maps.epcounty.com/arcgis/rest/services/Website_Basemap/MapServer/10` or its service parent. The same official portal item, `0b4e626d91684cecb1e35828cf52092f`, now identifies `https://maps.epcountytx.gov/arcgis/rest/services/Website_Basemap/MapServer` with sublayer 10 in its operational layer configuration. A live read of the new `/10` identifies `EPCounty_Commissioner_PCT`, `esriGeometryPolygon`.

This is a source-host migration requiring a separate bounded source-contract reconciliation, including old/new endpoint equivalence and precinct snapshot checks. No arbitrary hostname alias, source substitution or contract bypass was added here. The downstream precinct and Census checks did not execute in the failing run.

### LIC-G5 dependency-lock drift

[Run 38577370717](https://github.com/MightyLoud/Civic-Cartography/actions/runs/38577370717) reports only `lock_matches_generated=false`; its repeated lock generation, dependency audit, YAML and regression checks passed. The workflow deletes its temporary locks and resolves floating requirements against the current package index, then compares the generated bytes to `requirements-dev.lock`.

The log and committed lock establish these version differences:

| Package | Committed lock | Fresh resolution |
| --- | --- | --- |
| anyio | 4.14.2 | 4.15.1 |
| idna | 3.18 | 3.20 |
| iniconfig | 2.3.0 | 2.3.1 |
| pygments | 2.20.0 | 2.21.0 |
| rpds-py | 2026.6.3 | 2026.9.1 |

This is independently reproducible dependency freshness drift, unrelated to geography. Whether LIC-G5 should enforce latest dependency freshness or exact approved-lock reproduction is a policy decision. No dependency versions, hashes or gate conditions were changed as part of the geography correction.

## Verification and remaining action

- Original local regression suite: 202 passed.
- Focused corrected TIGERweb tests: 32 passed.
- Corrected full local regression suite: 222 passed.
- Normalized dataset validation: passed for 34 files.
- GeoJSON and join validation: passed.
- Direct CLI generation for county, place and school-district sources: passed; all generated `source_vintage=2026-01-01`.
- Direct fresh Travis and Denton comparisons: failed as expected with named coordinate, attribute and vintage differences; fresh raw/canonical support checks passed.
- No tracked `data/`, `evidence/` or workflow files were changed. No merge, manual dispatch, release, schedule or source-system write was performed.

Next action: review the code correction separately from PR #480, then prepare a bounded baseline reconciliation. Preserve old raw evidence; capture fresh responses and their metadata; quantify changed polygons and address-control impact; reconcile authority, vintage, joins and source manifests; approve each release before replacing its baseline. Handle the El Paso host migration and LIC-G5 lock policy as separate changes. PR #480 remains a draft manual-only preflight; this investigation does not establish complete Civic Monitoring v0.5 operation or change `GATE-CM-006` from `WAIT`.

## October 14 code review follow-up

Review reproduced an integer-normalization edge case: Python considers `False == 0` and `0.0 == 0`. After normalizing a stored `"0"`, the earlier comparator could accept these unsupported source types. The comparator now accepts only nonnegative JSON integers or ASCII digit strings for the two area fields, rejecting booleans, floats, nulls, negative values and decimal strings before comparison. Eight additional regression cases cover this rejection.

After this correction: 40 focused TIGERweb tests passed; the full local suite passed 230 tests; 34-file normalized validation and GeoJSON validation passed. The earlier 222-test GitHub result refers to commit `51a05895e374b45b96788064c49629148c509294`, before these eight new cases. No approved baseline or workflow was changed by the review correction.
