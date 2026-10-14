# TIGERweb baseline reconciliation — prepared, not approved

Eighteen candidate snapshots were captured from the exact source URLs recorded in the approved baselines on October 14, 2026. The [capture manifest](../evidence/tigerweb-baseline-preparation-20261014/manifest.json) records source URLs, capture timestamps, baseline/raw/candidate SHA-256 values, source vintage, measured differences and review status. All approved `data/` files remain unchanged.

This preparation depends on PR #481's reviewed correction at `289b27ce6e72c6fc2481b75748c3dc9cc1b48586`. It provides evidence for a future release decision; it does not approve a baseline replacement. PR #480 remains a separate draft manual-only connectivity preflight.

## Review disposition

The review of PR #481 reproduced an unsupported-type comparison edge case and corrected it: boolean, float, null, negative and decimal-string area values now fail closed. The corrected code passed 40 focused tests and 230 full tests locally. [GitHub's Irving run](https://github.com/MightyLoud/Civic-Cartography/actions/runs/38590551069) independently passed 230 tests, 34-file normalized validation and GeoJSON validation on the same commit.

The code is prepared for human review. No merge is authorized by this preparation. Geography CI remains blocked on source/vintage differences; the independent El Paso host migration and LIC-G5 lock drift remain unresolved.

## Measured coverage differences

The source polygons were validated and projected from EPSG:4326 into EPSG:5070 for area and distance measurement. No source coordinates were snapped, buffered, simplified, rounded or repaired. These are diagnostic measurements, not acceptance thresholds. Distance is projected Hausdorff distance; percentage is symmetric-difference area divided by the stored polygon area, not net area loss.

| Boundary | Added coverage (m²) | Removed coverage (m²) | Coverage difference | Hausdorff distance (m) |
| --- | ---: | ---: | ---: | ---: |
| Oak Point | 429,055.42 | 1,356,449.19 | 11.1695153% | 845.921 |
| Denton County | 347,218.27 | 71.39 | 0.0140900% | 66.209 |
| Carrollton-Farmers Branch ISD | 25.25 | 29,766.15 | 0.0238176% | 44.477 |
| Dallas County | 184.77 | 137,699.58 | 0.0058590% | 26.735 |
| Tarrant County | 0.00 | 5,742.91 | 0.0002453% | 18.079 |
| Collin County | 12.51 | 27.65 | 0.0000018% | 0.041 |
| Harris County | 5.89 | 2.59 | 0.0000002% | 0.027 |
| Travis County | 0.20 | 0.19 | Less than 0.0000001% | 0.013 |
| Williamson County | 0.19 | 0.20 | Less than 0.0000001% | 0.013 |

The other nine polygons have unchanged coordinates and zero coverage difference: Montgomery, Fort Bend, Hidalgo, Galveston, Kaufman, Bexar and Kerr counties; Arlington; and Olmos Park. Five of these still have changed source area values. The other four have equivalent integer values represented differently. All 18 candidates carry the verified 2026 vintage instead of the approved baseline's 2025 label.

Oak Point is the highest-priority authority reconciliation. Its gross changed coverage is approximately 1.786 km², with a net reduction of approximately 0.927 km². These observations do not identify the underlying legal action or establish that the fresh polygon is the correct present municipal boundary.

## Address-lookup limits

All 36 old/new Census internal-point checks remain covered by both the stored and candidate polygons. This provides interior consistency evidence, but it is not an address-control test.

Seventeen explicitly synthetic probes in the added/removed coverage demonstrate the predicted membership change for the nine changed polygons. These computed points are labeled `real_address=false` and must not be counted as physical-address controls or actual affected addresses.

No suitable trusted physical-address coordinate controls for these Texas cases were found in the inspected repository. Real-address impact remains `UNVERIFIED`. Candidate-to-normalized geometry joins were dry-run in a disposable overlay and passed; that validates identifiers, not source authority or release readiness.

The City of Oak Point's [Planning & Engineering page](https://www.oakpointtexas.com/173/Planning-Engineering) currently links a live public ArcGIS experience, `ba87aee73fc74607bcca8cd8356071f2`, owned by `OakpointDevelopment`. It resolves to web map `8bd15c6337ea45c3b572936116f7b3a6` and its City Boundaries layer at `Landmark_Base_GC/MapServer/1`, published by `DentonCountyGIS`. The October 2022 static zoning PDF located earlier is historical context, not the current link. This corrects the earlier map-source note.

The live county query returns separate `TYPE=CITY` and `TYPE=ETJ` features. Only the city-limit feature (`INC_MUNI=OAK POINT`, `CityCode=OAKP`) was compared; ETJ was excluded. Its last-edited timestamp is February 17, 2026, which is not a verified legal effective date. The county city-limit polygon differs from stored Census coverage by 12.8975% and from fresh Census coverage by 1.8180%, relative to the county polygon. Fresh Census remains different by approximately 273,340 m² and 598.457 m projected Hausdorff distance. This independent official source narrows the investigation but does not resolve it or approve replacement.

The [Oak Point authority evidence](../evidence/tigerweb-baseline-preparation-20261014/oak-point-authority/) preserves the source graph, raw city/ETJ query, fresh Census response, comparison measurements and blocked disposition. A previous `PoliticalBoundaries_GC` metadata request returned HTTP 403; the city-linked `Landmark_Base_GC` endpoint was accessible. No inaccessible source was substituted and no outreach was sent.

## Bounded review order

| Review batch | Members | Required decision |
| --- | --- | --- |
| Unchanged coordinates, equivalent values | Galveston, Kaufman, Arlington, Olmos Park | Review 2026 provenance and preserve identical geometry; no automatic release |
| Unchanged coordinates, changed area values | Montgomery, Fort Bend, Hidalgo, Bexar, Kerr | Reconcile source attributes and metadata; do not discard actual value changes |
| Small measured coordinate changes | Travis, Williamson, Harris, Collin | Determine upstream correction/precision cause and check relevant address controls; size alone does not approve a change |
| Larger measured coverage changes | Oak Point, Denton, CFBISD, Dallas, Tarrant | Reconcile controlling authority and changed areas before replacing geometry; prioritize Oak Point |

Each release candidate must preserve the old raw evidence, verify the capture's hashes, reconcile identity/vintage/source manifests, and undergo its jurisdiction-specific checks. Appropriate address controls are required to establish real lookup effects. Do not promote the entire batch merely because the candidates validate structurally.

The fastest bounded pilot is one unchanged-coordinate candidate, such as Galveston, after code review and explicit baseline approval. Oak Point should be investigated independently in parallel with that review; it does not justify blocking unrelated non-geographic operations.

## Prepared evidence and verification

The [evidence directory](../evidence/tigerweb-baseline-preparation-20261014/) contains:

- 18 exact raw source responses and 18 canonical candidate snapshots with actual capture-date attribution;
- layer metadata captured before and after the batch for county, place and school-district sources;
- nine diagnostic added/removed-coverage GeoJSON files;
- the manifest with hashes, metrics, internal-point checks and synthetic probes; and
- a capture/analysis script with optional analysis dependencies isolated from production requirements.

Verified: all 18 raw/canonical support checks, all 36 baseline/candidate polygon validity checks, candidate identity/attribution preservation, all recorded file hashes, projected area conservation within floating-point measurement precision, and the full candidate-overlay join validation. Source vintage remained 2026-01-01 across capture. Approved baseline hashes remain unchanged.

Still blocked: baseline replacement approval, real-address impact, legal/upstream explanations for changed coverage, El Paso source-host reconciliation and LIC-G5 lock policy. No production workflow, source manifest, normalized record, official geometry or monitoring gate was changed by this evidence preparation. Neither PR was merged or manually dispatched.

To reproduce a new capture, use a separate copy of the evidence directory with no existing `capture/` folder. Install the versions in `analysis-requirements.txt` in a temporary environment, then execute `prepare.py`. The script deliberately refuses to overwrite an existing capture. Its optional dependencies are not imported by production validators or added to `requirements-dev.txt`.
