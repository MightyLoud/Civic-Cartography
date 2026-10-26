# CFBISD authority review — source conflict remains unresolved

The bounded follow-up to [the Census investigation](cfbisd-source-investigation-20261026.md) found operational sources that disagree with the proposed Census polygon in the changed areas. The state district layer, Denton County's district polygon and CFBISD's own public locator all include three explicitly synthetic points that the fresh Census polygon excludes. These publications may share underlying linework; their lineage is not established and their agreement is not three independent legal confirmations.

No baseline replacement is supported by this review. All approved geometry, identifiers, strict comparisons, election evidence and release restrictions remain unchanged. The evidence package is `CFBISD-AUTH-001`, retained in [cfbisd-authority-review-20261026](../evidence/cfbisd-authority-review-20261026/). Capture times and source dates are recorded separately.

## Source routing and dates

| Publication | Verified routing and source date | Limit |
| --- | --- | --- |
| CFBISD [School Search](https://www.cfbisd.edu/students/school-maps-locator-system) | Official district page embeds the public GuideK12/Frontline locator. Its page describes attendance zones approved March 6, 2025. The public `schools_spatial` read operation was queried at retained coordinates. | Attendance zones and lookup results do not prove an outer-district boundary action or legal placement. |
| [TEA locator](https://tea.texas.gov/families-and-students/school-district-locator/school-district-locator) | App `51f0c8fa684c4d399d8d182e6edd5d97` → web map `15ce858b4ad5408480950db704fd455a` → `School_Districts__2026/FeatureServer/0`, named `SchoolDistricts_SY2526`. Queried `NCES_DISTR = '4813050'`. | The app's search widget still references `Current_Districts_2023`; the displayed operational layer is the 2025–26 source actually used for comparison. Neither label alone guarantees a recent geometry edit. |
| [State district layer](https://services2.arcgis.com/5MVN2jsqIrNZD4tP/arcgis/rest/services/School_Districts__2026/FeatureServer/0) | Published metadata identifies 2025–26 school districts assembled by the Texas Legislative Council from TEA and appraisal-district inputs, using 2020 TIGER/Line base geography with further corrections. | The state explicitly describes this as reference data, not a legal land description or determination of jurisdictional authority. |
| [Denton County ISD](https://gis.dentoncounty.gov/arcgis/rest/services/ISD_GC/MapServer/0) | One `ISD = Carrollton-Farmers Branch` feature, local `DIST_CODE = 012`; returned edit timestamp May 14, 2026, 14:48:27 UTC. | The local code is a source identifier, not a replacement for Census GEOID `4813050` or the repository IDs. Edit time is not a legal effective date. |
| [Denton County 911 addresses](https://gis.dentoncounty.gov/arcgis/rest/services/Addresses911Permits_GC/MapServer/0) | Three bounded-envelope queries returned 0 north, 9 west and 0 near the inserted-vertex sliver. All nine returned records carry `UpdateDat = 2021-02-11T00:00:00Z`. | Source address points have not been independently field-validated. Three distinct address records share one coordinate. |
| [Denton County CAD parcels](https://gis.dentoncounty.gov/arcgis/rest/services/CAD_GC/MapServer/0) | Bounded queries returned 11 north and 14 west features; no feature near the inserted sliver. There are 21 unique property IDs. Twenty-four features carry `prop_val_yr = 2027`; one has an unknown year and unknown school fields. | The 2027 value is an appraisal-year field captured in October 2026. It is not evidence of the legal boundary in effect in 2026. Parcel labels do not establish that every part of a parcel belongs to that district. |

[source-discovery.json](../evidence/cfbisd-authority-review-20261026/source-discovery.json) retains the official entry points, selected routing fields, metadata hashes and capture records. Full discovery HTML/UI configurations are not redistributed. Exact target GeoJSON responses and source metadata are retained; the large state layer metadata is losslessly gzip-compressed with a Base64 text wrapper. Public map-client credentials and unrelated application JavaScript are excluded from the package.

TEA's [locator FAQ](https://tea.texas.gov/families-and-students/school-district-locator/school-district-locator-faq) distinguishes district boundaries from attendance zones, identifies the district and county appraisal/taxing authorities as verification sources, and explains that mapped approximations do not settle legal boundary questions. The state [dataset catalog](https://data.capitol.texas.gov/dataset/school-districts) also directs detailed boundary questions to the appropriate county appraisal district. No controlling legal description, boundary order or specific Census correction record for these two segments was located in this bounded review.

## Four synthetic changed-area probes

These are the exact probes retained in the earlier investigation. They are computed points, not addresses. The direct district requests used coordinate lookup, not geocoding or address text. The district's `in_district` boolean is reported as an operational lookup result.

| Probe | Retained Census | Fresh Census | TEA 2025–26 | County ISD | District locator |
| --- | --- | --- | --- | --- | --- |
| North added patch | Outside | Inside | Inside | Inside | Inside |
| Inserted-vertex removed sliver | Inside | Outside | Inside | Inside | Inside |
| North replacement, removed patch | Inside | Outside | Inside | Inside | Inside |
| West replacement, removed patch | Inside | Outside | Inside | Inside | Inside |

The internal Census-point control is inside all five representations. All four polygons are valid. The state and county polygons also differ from both Census versions elsewhere: projected whole-polygon symmetric differences are approximately 50,667 m² and 92,535 m² against the retained Census polygon, and 80,393 m² and 122,261 m² against the fresh polygon, respectively. These EPSG:5070 diagnostics do not select a winner, establish shared lineage, or create an acceptance threshold.

The disagreement therefore remains substantive. A vintage relabel, regeneration, or acceptance of the latest Census fetch cannot resolve it. Source publication agreement must not be promoted to legal certification.

## Bounded address and parcel checks

All six feature queries were reconciled against separate server count queries. Returned counts match exactly and no transfer-limit flag is present. The records are the results of the specified server envelope queries; client-side geometry membership is evaluated at the exact returned coordinates. They are not an exhaustive address inventory or a guarantee that the server's projected-envelope filter exactly matches a longitude/latitude rectangle.

The nine source address records represent seven unique coordinates. All nine have the same retained/fresh Census membership; the state polygon, county polygon and district locator agree for those sampled points. Four records are inside all five representations and five records are outside all five. Three `RAILROAD` address records coincide at one point and are not counted as three independent spatial controls.

**The sample has zero computed old/new membership changes. Overall real-address impact remains `UNVERIFIED`.** Old update dates, duplicate coordinates, uncertain positional quality and limited spatial coverage prevent a conclusion of zero affected addresses or legal assignment. Full source IDs, coordinates and results are retained in [address-controls.csv](../evidence/cfbisd-authority-review-20261026/address-controls.csv).

Fourteen parcel features have positive-area overlap with the removed Census coverage. Their returned labels are three `CARROLLTON-FB ISD`, ten `LEWISVILLE ISD`, and one unknown. The northern overlapping property is `86140`, labeled CFBISD. Western overlaps include CFBISD-labeled `225342` and `225343`, ten Lewisville-labeled records, and unknown `336972`. These are diagnostic intersections, not determinations that any whole property changed districts. The area calculations preserve the original source coordinates; no snapping, buffering, rounding, simplification or repair is used.

[parcel-overlaps.csv](../evidence/cfbisd-authority-review-20261026/parcel-overlaps.csv) retains source property IDs, year fields, labels, situs values and computed overlap areas. Unknown year and school fields remain blank/unknown. No owner names, owner mailing addresses or occupant information were requested.

## Exact remaining adjudication

The useful next evidence is the controlling linework and correction history for the two replaced segments, rather than another identical Census capture:

1. **North/Rosemeade segment:** reconcile prior ring range `[568,582)` with fresh `[569,578)`, including their shared neighboring vertices. Explain the retained CFBISD parcel label for property `86140` and the three non-Census sources' inclusion of the northern removed-area probe.
2. **West segment:** reconcile prior `[751,784)` with fresh `[747,764)`. Explain the mixed appraisal-district labels and the disagreement at the western removed-area probe. A whole-parcel label alone cannot supply the line.
3. **Source history:** identify the authority and document supporting the line, whether the Census edits represent a spatial correction or an actual district-boundary action, and the applicable source/legal dates. The original hard-coded 2025 label does not establish those dates.
4. **Lookup effects:** validate trusted address coordinates on both sides of the disputed lines and distinguish address-point membership, parcel attribution, attendance eligibility and legal jurisdiction.

The repository record and geometry IDs remain `TX:school_district:carrollton-farmers-branch-isd:at_large:DISTRICTWIDE` and `carrollton-farmers-branch-isd-districtwide`; Census GEOID remains `4813050`. No alternative source polygon is adopted. The technical adjudication packet is prepared; no source communication was sent.

## Review files and QA

- [analysis.json](../evidence/cfbisd-authority-review-20261026/analysis.json): counts, limits, source conflicts, diagnostics and blocked disposition.
- [probe-comparisons.csv](../evidence/cfbisd-authority-review-20261026/probe-comparisons.csv): synthetic, address-source and internal-point results with distinct evidence types.
- [review-overlay.geojson](../evidence/cfbisd-authority-review-20261026/review-overlay.geojson): four exact source polygons and twelve uniquely located review probes for QGIS or another GIS viewer. This is a review overlay, not a canonical dataset.
- [reproduce.py](../evidence/cfbisd-authority-review-20261026/reproduce.py): offline regeneration using the earlier investigation's optional analysis requirements; refuses to overwrite its five derived outputs.

Source hashes, lossless decompression, district identity, query completeness, duplicate-coordinate handling, probe classification and release holds are checked by the added regression tests. Local and GitHub validation results are recorded in draft PR #502. Original source snapshots and the prior evidence package remain unchanged.
