# CFBISD source mismatch — investigation and bounded draft correction

The CFBISD failure on draft PR #501 is reproducible source-content drift from the retained baseline. It includes a different polygon and changed land-area and centroid values; changing only the vintage label cannot resolve it. The verified current layer describes January 1, 2026 vintage. The old snapshot's 2025 label was hard-coded by its original generator, so that label alone does not independently prove the historical source vintage or explain the geometry changes.

The approved CFBISD boundary remains unchanged. This draft adds evidence, regression checks, and one operational correction: retain the existing boundary-check artifact after a strict comparison failure. It does not make the Census comparison pass or authorize a baseline replacement.

## PR and workflow evidence

Inspected October 26, 2026; exact API results and log excerpt are retained in [github-state.json](../evidence/cfbisd-source-investigation-20261026/github-state.json).

| Item | Verified state |
| --- | --- |
| [Williamson PR #501](https://github.com/MightyLoud/Civic-Cartography/pull/501) | Open, draft, unmerged; head `18088213e74ac42cb2932227d1ad7ede2ebffadc`; 22 completed PR workflows: 12 successful, 10 failed |
| [Williamson workflow 40266430127](https://github.com/MightyLoud/Civic-Cartography/actions/runs/40266430127) | Successful |
| [CFBISD workflow 40266429807](https://github.com/MightyLoud/Civic-Cartography/actions/runs/40266429807/job/121389747115) | Failed at `Verify committed CFBISD boundary matches Census`; tests, dataset validation, joins and artifact upload skipped in this job |
| [Travis PR #500](https://github.com/MightyLoud/Civic-Cartography/pull/500) | Open, draft, unmerged; head `dbdfd06b0a23097692f5dd5dd70d8392e1c36d98` |
| [Earlier CFBISD workflow 40028432028](https://github.com/MightyLoud/Civic-Cartography/actions/runs/40028432028/job/120670368839) | Same failed step and same geometry/AREALAND/CENTLAT/CENTLON/source_vintage diagnostic on October 23 |

The CFBISD raw and canonical files, generator, metadata helper, strict comparator and workflow are byte-identical between the #500 and #501 heads. The failure therefore predates Williamson's changes; nothing found attributes this discrepancy to #501. The other failed #501 workflows were enumerated, not diagnosed by this bounded investigation.

The failed #501 CFBISD run has no artifact. Its upload step used the default success condition, so the comparison failure skipped the evidence upload. Adding `if: ${{ always() }}` to that existing upload is the smallest supported workflow correction. The comparison still fails with exit code 1, and subsequent success-only test steps still skip after that failure. There is no `continue-on-error`, fallback acceptance, tolerance, comparator edit or manual dispatch.

## Census and prior-work reconciliation

Two independent requests to the exact recorded [Census Current layer 14 query](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/14/query?where=BASENAME+LIKE+%27%25Carrollton-Farmers+Branch%25%27&outFields=%2A&returnGeometry=true&outSR=4326&f=geojson) completed at 13:30:03 and 13:30:14 UTC on October 26. [Official metadata](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/14?f=json) was captured before and after each query. All four metadata responses identify `Unified School Districts; January 1, 2026 vintage`. Each response contains exactly the expected district, GEOID `4813050`.

Both raw server responses match byte for byte: SHA-256 `c3982123587aa1ff1fb576ec30948c33d00774539726d00d92daada6f0d36bbf`. This is also the exact raw-response hash recorded in the October 14 preparation at commit `dc148ab3c4b9be2034777f48cdc86d3dbe40cb86`, branch `draft/tigerweb-baseline-preparation-20261014`. The earlier raw and canonical files are retained with their source commit and hashes. This demonstrates recurrence of the previously investigated content, not a newly discovered October 26 edit.

Both freshly generated candidates are also byte-identical. All four pairs—approved baseline, October 14 evidence and both October 26 captures—pass raw/canonical support checks. The existing canonicalizer regenerates both fresh candidates exactly. Source identity, repository joins and all other stable source attributes remain consistent. The old release generator at commit `7fc99f6` explicitly hard-coded `source_vintage = 2025-01-01`; no historical layer metadata proving that date was located in the inspected release evidence.

| Field | Retained baseline | October 26 Census candidate |
| --- | --- | --- |
| `GEOID` | `4813050` | `4813050` |
| `source_vintage` | `2025-01-01` (stored label) | `2026-01-01` (metadata verified) |
| `AREALAND` | 122,372,279 m² | 122,342,541 m² (−29,738) |
| `AREAWATER` | 2,709,073 m² | 2,709,073 m² |
| `CENTLAT` | `+32.9460217` | `+32.9460108` |
| `CENTLON` | `-096.9133555` | `-096.9133531` |
| Ring vertices, including closure | 1,020 | 1,000 |
| `source_retrieved_at` | `2026-08-01` | `2026-10-26` (actual new capture date) |

Area-string versus integer representation is already normalized by the strict comparator. The land-area values actually differ. ArcGIS bookkeeping fields remain handled by the established comparator; none explains away the polygon, centroid or land-area differences.

The workflow deliberately supplies the old retrieval date as a replay label. Replaying the fresh candidate with that label, only in memory, exactly reproduces its diagnostic:

```text
geometry changed; source attributes changed: AREALAND, CENTLAT, CENTLON; canonical properties changed: source_vintage
```

The preserved candidates retain their actual October 26 retrieval attribution. Relabeling the baseline alone would leave geometry, land area and both centroid fields different.

## Exact coordinate and coverage evidence

[coordinate-edits.json](../evidence/cfbisd-source-investigation-20261026/coordinate-edits.json) enumerates every altered coordinate. Applying its three edits in reverse index order reconstructs the new polygon exactly. Ranges below are zero-based and half-open; no coordinate is rounded, snapped, simplified or repaired.

| Operation | Prior ring range | Fresh ring range | Prior/new vertices |
| --- | --- | --- | --- |
| Insert | `[381,381)` | `[381,382)` | 0 / 1 |
| Replace | `[568,582)` | `[569,578)` | 14 / 9 |
| Replace | `[751,784)` | `[747,764)` | 33 / 17 |

973 vertices remain identical and in sequence. The two replacement segments remove 47 prior vertices and introduce 26 new vertices, plus the separate inserted vertex. This is not the three-insertion pattern in the Travis and Williamson drafts.

Both polygons are valid and are not topologically equal. Using unmodified EPSG:4326 coordinates projected to EPSG:5070 reproduces the October 14 diagnostics:

| Diagnostic | Measurement |
| --- | ---: |
| Added coverage | 25.253962 m² |
| Removed coverage | 29,766.147070 m² |
| Symmetric difference | 29,791.401033 m² |
| Difference as share of baseline area | 0.0238176168% |
| Net projected coverage change | −29,740.893108 m² |
| Projected Hausdorff distance | 44.476542 m |

These measurements describe source polygons, not legal changes or acceptance thresholds. Projected polygon areas and Census's source area attributes are separate measurements; no explanation for their differences is inferred. Both old/new Census internal-point checks remain covered by both polygons. The generated changed-area probes in [analysis.json](../evidence/cfbisd-source-investigation-20261026/analysis.json) are explicitly synthetic (`real_address=false`); they demonstrate geometric membership differences, not affected physical addresses.

## Disposition and smallest baseline proposal

**Verified:** current 2026 metadata; stable repeatable Census content; actual polygon/land-area/centroid drift; exact agreement with October 14 raw evidence; preserved joins; successful raw/canonical support; a pre-existing CI failure.

**Unverified:** the upstream edit cause, historical source-vintage transition date, any legal boundary action or legal effective date, controlling district-boundary confirmation for the two replaced segments, and real-address lookup effects. A source-vintage mismatch is present, but does not establish why the source geometry changed. No baseline replacement is authorized by these findings.

The smallest eventual baseline proposal, after authority/address review and explicit geometry approval, is:

1. Archive the existing CFBISD raw and canonical bytes under their original August 1 retrieval label and verify the retained hashes.
2. Replace only the CFBISD raw/canonical Census snapshots with the specifically approved candidate; retain GEOID `4813050`, `record_id = TX:school_district:carrollton-farmers-branch-isd:at_large:DISTRICTWIDE` and `geometry_id = carrollton-farmers-branch-isd-districtwide`.
3. Record verified 2026 metadata and actual capture-date attribution; update only the Census manifest row and the CFBISD workflow's retrieval replay label to the approved capture date. Preserve election, candidate, officeholder and cumulative-voting evidence and dates.
4. Re-run strict fresh-source comparison, regeneration, the full regression suite, 33-file dataset validation and geometry joins. Keep the existing geographic-governance and production-release holds.

That proposal is not applied here. The current draft implements only failure-artifact retention, evidence preservation and regression coverage. #500 and #501 remain draft and unmerged. No production promotion, governance closure, release activation, source communication or manual workflow dispatch is part of this work.

## Reproduction and validation

The [evidence folder](../evidence/cfbisd-source-investigation-20261026/) contains exact baseline copies, October 14 evidence, two fresh raw/canonical pairs, four metadata responses, request times/headers, hashes, exact coordinate edits, projected diagnostics, source-state evidence and reproducible capture/analysis scripts.

`capture.py NEW_DIRECTORY` refuses an existing output directory. `analyze.py` reads only the retained files and refuses to overwrite existing derived outputs. Optional analysis dependencies are isolated in `analysis-requirements.txt`; production dependencies and lockfiles are unchanged. To reproduce analysis, work on a disposable copy with only the two derived output files omitted.

Validation: all 272 local tests passed, including 46 CFBISD and TIGERweb checks. Normalized validation passed for 33 files; GeoJSON joins passed; whitespace checks passed. The disposable local environment used the analysis versions recorded in `analysis.json` and did not reproduce the entire repository dependency lock. GitHub's locked-environment checks remain separate. No local result is represented as a passing live-source workflow on this unchanged boundary.
