# CFBISD Census publication history

The annual 2026 TIGER/Line publication corroborates the fresh TIGERweb representation of GEOID `4813050`. This establishes a published Census source revision beyond a changed vintage label. The specific upstream correction, its authority and any legal boundary action remain unverified. The [previous authority conflicts](cfbisd-authority-review-20261026.md) remain unresolved, so no approved geometry or release hold changes.

## Annual Census evidence

Exact target SHP record bytes, DBF header/record bytes, native coordinates, attributes, archive/member hashes, source CRS and capture metadata are retained in [cfbisd-source-lineage-20261026](../evidence/cfbisd-source-lineage-20261026/). The complete Texas ZIPs were downloaded and checked against these excerpts; they are publicly available at the links below and are not duplicated in the repository.

| Representation | Ring vertices, including closure | Land area (m²) | Water area (m²) |
| --- | ---: | ---: | ---: |
| Retained TIGERweb baseline | 1,020 | 122,372,279 | 2,709,073 |
| [2024 TIGER/Line](https://www2.census.gov/geo/tiger/TIGER2024/UNSD/tl_2024_48_unsd.zip) | 1,018 | 122,372,374 | 2,709,073 |
| [2025 TIGER/Line](https://www2.census.gov/geo/tiger/TIGER2025/UNSD/tl_2025_48_unsd.zip) | 1,018 | 122,372,375 | 2,709,073 |
| [2026 TIGER/Line](https://www2.census.gov/geo/tiger/TIGER2026/UNSD/tl_2026_48_unsd.zip) | 1,000 | 122,342,541 | 2,709,073 |
| October 14/26 Current TIGERweb captures | 1,000 | 122,342,541 | 2,709,073 |

The 2024 and 2025 native rings are exactly identical, despite a 1 m² difference in their published land-area attributes. The 2026 native ring differs from 2025. Neither older annual product reproduces the retained baseline's vertex count and area. Therefore this review does **not** establish that the baseline is a faithful 2025 annual snapshot. Its original hard-coded vintage label remains insufficient evidence.

The 2026 annual coordinates use NAD83; the captured TIGERweb response uses EPSG:4326 after ArcGIS export. The raw coordinate values are not exactly equal even after allowing ring rotation and reversal. At seven decimal places, their rings agree after rotation/reversal. This is a publication-history diagnostic, not exact coordinate equality, a geodetic precision claim, or a new acceptance threshold. Original doubles are preserved. Production comparisons use no rounding, snapping, repair or simplification. Regression coverage demonstrates that a coordinate change concealed by this diagnostic still fails the strict comparator.

Exact 2025-to-2026 native coordinate edit ranges are recorded in [analysis.json](../evidence/cfbisd-source-lineage-20261026/analysis.json). They include the 33-to-17 and 14-to-9 replacements but also other edits. They must not be substituted for the different baseline-to-candidate edit sequence documented in the [original investigation](cfbisd-source-investigation-20261026.md).

## Archived 2026 verification listings

The official [2026 SDRP verification archive](https://www2.census.gov/geo/pvs/sdrp/2026verification/48_Texas_verificationlistings.zip) was captured unchanged and preserved losslessly as Base64 text, with its ZIP hash and response metadata. The current program landing page describes the next cycle; the archived directory supplies this 2026 evidence.

The school-district inventory, `sheet 1`, row 145 identifies state `48`, SDLEA `13050`, grades `PK`–`12`, level `U`, a blank `SDTYPE`, and CFBISD's unchanged name. The county-coverage workbook, `sheet 1`, rows 338 and 371 lists Dallas (`113`) and Denton (`121`). The joined Census identifier is still `4813050`; these fields do not replace repository identifiers.

Both workbooks contain inventory/coverage columns only. There is no geometry, change-reason field, correction record or legal-effective-date field. A blank `SDTYPE` is not a boundary-change flag. These listings corroborate identity and county relationships, not the cause of the revised line. Exact cells, source workbook hashes and row counts are retained in the analysis; no workbook was edited or recalculated.

## Public-record review and disposition

The bounded public review included these annual products, archived SDRP listings, the official March 6, 2025 [district agenda](https://meetings.boardbook.org/Public/Agenda/631?meeting=676287), and targeted indexed searches for CFBISD boundary/annexation/correction records. Agenda item 6.B addresses campus consolidation and attendance zones. It does not establish an outer-district transfer. This was not an exhaustive board-minutes or legal-record audit.

Census's general [Boundary Change Notes](https://www.census.gov/programs-surveys/geography/technical-documentation/boundary-change-notes.html) cover other listed geography types; their stated scope excludes school districts. An absent CFBISD entry cannot establish that no school-district revision occurred. The specific controlling line description or Census correction record was not located in this bounded review. This is a finding about the reviewed evidence, not proof that no such record exists.

The smallest supported operational correction remains the existing failure-artifact upload in draft #502. A vintage-only edit would leave geometry, land area and centroid mismatches. Replacing the boundary would bypass unresolved state/county/district conflicts. A further data correction requires the source record explaining the northern Rosemeade and western replacements, their applicable dates, and adjudication of the exact segments and trusted point controls already identified in the authority packet.

No canonical dataset, original snapshot, generator, comparator, dependency lock, established identifier or release restriction was changed. All draft PRs remain unmerged. No outreach, manual dispatch or production promotion was performed.

## Reproduction

Run `python evidence/cfbisd-source-lineage-20261026/reproduce.py`. It decodes and checks original target record bytes and the unmodified verification workbooks using only the Python standard library, then prints the derived analysis. `--verify-archives /path/to/zips` additionally checks every original annual ZIP/member hash and extracts the same target records through their SHX/DBF offsets. `--output /new/path.json` refuses to overwrite existing evidence.

The added regression tests check source-byte decoding, stable identities, annual area/geometry distinctions, inventory limits, reproducible output and preservation of strict comparison below the diagnostic rounding precision.
