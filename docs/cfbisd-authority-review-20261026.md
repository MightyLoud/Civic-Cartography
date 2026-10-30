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

The [annual Census publication follow-up](cfbisd-source-lineage-20261026.md) corroborates the current 2026 source revision and checks archived SDRP listings. It does not resolve the authority conflicts or identify a controlling correction/action record. The original review and its source snapshots remain intact.

- [analysis.json](../evidence/cfbisd-authority-review-20261026/analysis.json): counts, limits, source conflicts, diagnostics and blocked disposition.
- [probe-comparisons.csv](../evidence/cfbisd-authority-review-20261026/probe-comparisons.csv): synthetic, address-source and internal-point results with distinct evidence types.
- [review-overlay.geojson](../evidence/cfbisd-authority-review-20261026/review-overlay.geojson): four exact source polygons and twelve uniquely located review probes for QGIS or another GIS viewer. This is a review overlay, not a canonical dataset.
- [reproduce.py](../evidence/cfbisd-authority-review-20261026/reproduce.py): offline regeneration using the earlier investigation's optional analysis requirements; refuses to overwrite its five derived outputs.

Source hashes, lossless decompression, district identity, query completeness, duplicate-coordinate handling, probe classification and release holds are checked by the added regression tests. Local and GitHub validation results are recorded in draft PR #502. Original source snapshots and the prior evidence package remain unchanged.


## October 29, 2026 — TLC response and qualified hypothesis review

**Disposition: AGENCY RESPONSE RECEIVED; SOURCE/SEGMENT AUTHORITY STILL UNRESOLVED.** This dated addendum supplements the original October 26 observations; it does not retroactively change their capture dates, findings or snapshots.

The established official email thread was read directly. Charles Eckstein, Texas Legislative Council (TLC), Research Division, Mapping and Redistricting Section, replied on October 29, 2026 at 17:27:27 UTC, after TEA's Julia Schacherl added him at 15:53:52 UTC. In paraphrase, he reports that TLC's records identify December 2018 as its last CFBISD SDRP submission on TEA's behalf, requesting a minor alignment correction from Dallas County Central Appraisal District geography. He suggests that 2010-versus-2020 Census TIGER base geography may explain differences and reports subsequent slight school-district/county movements from base geography. His office does not possess the district's controlling field notes, metes-and-bounds description or official survey map. This is an attributed records-history statement and suggested explanation, not a supplied submission, geometry file, Census processing receipt or legal boundary instrument. The private source message and headers were verified in Gmail; private mailbox identifiers, routing headers, signatures and full correspondence are not redistributed here. No spatial submission attachment accompanied the substantive reply; inline signature images are not boundary evidence.

### What the response changes

| Hypothesis or claim | Assessment against retained evidence |
| --- | --- |
| TLC submitted a recent CFBISD-specific SDRP correction for the 2026 cycle | Weakened by Charles's statement that December 2018 was the last submission in his records. Not ruled out for other submitters or Census internal processing; no exhaustive Census transaction history was supplied. |
| A spatial alignment correction, rather than a jurisdictional transfer, is a plausible explanation | Supported as a historical mechanism and investigation lead. His description concerns the 2018 request, not an adjudication of the exact 2026 changes. |
| The December 2018 request caused these exact 2026 edits | Unproven. No submitted coordinates, affected-segment map, acceptance record or processing/publication crosswalk was provided. Delayed processing or later realignment remains a hypothesis only. |
| A simple comparison of a 2010 product with a 2020 product explains the whole observed discrepancy | Insufficient as a complete account: the retained annual evidence compares 2024 and 2025 identical native rings with a different 2026 native ring. An older-base lineage could still underlie those publications, but must explain that later transition. |
| A recent legal boundary action occurred | Not established. A reported cartographic correction does not demonstrate annexation, detachment or transfer; absence of a newer submission in TLC's records is not proof no legal action occurred. |
| TLC's response legally certifies either polygon | Unsupported. Charles explicitly reports lack of controlling legal-description/survey records in his office. Operational publications remain reference evidence. |

The [annual-publication review](cfbisd-source-lineage-20261026.md) retains 1,020 vertices for the baseline; 1,018 for both 2024 and 2025 annual products; and 1,000 for 2026. The 2024/2025 rings are exactly identical despite their 1 m² AREALAND difference. The retained baseline is not an exact match for either annual product; its hard-coded 2025 label is not independently verified vintage evidence. Thus neither that label nor the proposed base-geography explanation establishes when or why the baseline linework originated. The 2026 annual/TIGERweb agreement remains corroborative publication evidence, not authority certification.

### Exact edits remain individually unassigned

Indices below refer only to the original baseline-to-current ring comparison (zero-based, half-open), not the separate annual-to-annual edit sequence. Original full-precision coordinates and neighboring geometry remain in [coordinate-edits.json](../evidence/cfbisd-source-investigation-20261026/coordinate-edits.json).

| Edit | Retained → current range | Outstanding attribution test |
| --- | --- | --- |
| Inserted vertex | [381,381) → [381,382), inserted coordinate (-96.83976499963819, 32.93985299999463) | Determine whether it appears in the 2018 submitted/exported line or a later base correction. The removed-sliver probe still conflicts with state, county and district operational representations. |
| North/Rosemeade | [568,582) → [569,578), 14 → 9 vertices | Obtain controlling linework and Census processing lineage for this exact replacement, shared endpoints and removed/added patches; reconcile property 86140 and the northern probe. |
| West | [751,784) → [747,764), 33 → 17 vertices | Identify the source for this exact replacement and reconcile properties 225342/225343, unknown 336972 and the western probe. Mixed parcel labels do not supply a controlling line. |

Neither fewer vertices nor apparently straighter segments proves simplification, improved accuracy or a lawful jurisdictional change. The two long replacements and inserted sliver must be attributed separately. No new spatial overlay was calculated in this addendum; existing probe and annual comparisons are preserved, not represented as newly executed.

### Bounded public-source search

Official public pages and targeted indexed searches were inspected for DCAD historical GIS, the 2018 submission and state historical school-district products. Capture/review date is October 29, 2026 (America/Denver); source descriptions retain their own dates.

- [DCAD GIS Data Products](https://dcadwebdev.dallascad.org/GISDataProducts.aspx) exposes an Independent School Districts ZIP via its SchoolTaxDistrict.zip download link. The download resolved as ZIP content, which the web reader could not inspect. Its bytes, CRS, coverage and geometry were therefore not validated. The page lists recent historical parcel products (2022–2026), not a dated 2018 school-district archive. Parcel history is not district-linework history. The page describes district-defined school boundaries and warns that GIS products are informational approximations, not surveys.
- [TLC's School Districts catalog](https://data.capitol.texas.gov/dataset/school-districts) exposes annual school-year shapefiles for 2021–22 through 2025–26 in the inspected listing. Those are potentially useful temporal controls, not the 2018 SDRP submission itself. The catalog warns that its boundaries do not determine jurisdictional authority.
- An [older TEA School Districts hosted layer](https://services.arcgis.com/su8ic9KbA7PYVxPS/ArcGIS/rest/services/TEA_School_Districts/FeatureServer/0) has metadata referring both to 2019–20 and to corrections for 2018–19 using a 2010 TIGER base. It exposes NCES_DISTR and SDLEA10 fields and EPSG:4269. Its last-edit metadata is June 24, 2024, so it is not a certified immutable 2018 snapshot. Only its metadata was inspected; no claim is made that its CFBISD polygon matches the submitted correction.
- [Census SDRP program documentation](https://www.census.gov/programs-surveys/sdrp/about.html) distinguishes annotation submissions from verification of their incorporation into MAF/TIGER. Both sides of that process are needed here. The existing 2026 inventory/coverage listings contain no edit geometry or causal transaction record.

**Result:** useful public retrieval routes located; no public copy of the specific December 2018 submission, historical DCAD source file used by TLC, or Census record linking it to these 2026 segments was located in this bounded search. This is not proof such records are unavailable or do not exist.

### Smallest next documentation request

A focused electronic reply in the established thread would materially improve adjudication. Proposed request, not sent:

Thank Charles and Julia for the records history, then ask for (1) the December 2018 CFBISD submission/export and accompanying map or correspondence, including the DCAD source file/version and CRS; (2) any Census acceptance/verification record and first publication incorporating that correction; and (3) whether the submission covers the linked north, west and inserted-vertex edits. Ask Census to identify any later MAF/TIGER base-alignment transaction affecting those segments, including source, reason and processing/publication dates. Request a custodian referral if the records reside elsewhere. Ask for an existing legal instrument and legal-effective date only if a jurisdictional action is asserted; do not infer one from a cartographic processing date.

Receipt of the original request (December 2018), source-data date, Census processing date, first publication vintage and any legal-effective date must remain separate. Attribution requires exact segment correspondence plus a documentary processing chain; legal authority additionally requires the controlling instrument or custodian confirmation of the applicable line. Electronic outreach remains subject to user approval.

Approved geometry, repository identifiers, original evidence, strict comparison behavior and all release restrictions remain unchanged. This addendum changes documentation only; it authorizes no baseline replacement, merge, workflow dispatch or release.
