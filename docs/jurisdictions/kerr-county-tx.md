# Kerr County, Texas

## Release scope

Kerr County is modeled as a bounded ten-office county schema:

- County Judge
- Commissioner Precincts 1-4
- Sheriff
- County Clerk
- District Clerk
- Tax Assessor-Collector
- County Treasurer

The release has five normalized geographies: one countywide record and four Commissioner precinct records. County Surveyor, prosecutorial offices, judges, justices of the peace, and constables remain explicit source evidence but are not silently folded into this bounded release.

## Current roster

| Office | Current holder | Current-entry method |
| --- | --- | --- |
| County Judge | Rob Kelly | Election |
| Commissioner Precinct 1 | Tom Jones | Election |
| Commissioner Precinct 2 | Rich Paces | Election |
| Commissioner Precinct 3 | Jeff Holt | Election |
| Commissioner Precinct 4 | Don Harris | Election |
| Sheriff | Larry L. Leitha Jr. | Election |
| County Clerk | Nadene Alford | Election; the prior court appointment expired December 31, 2024 |
| District Clerk | Eunavae Baublit Tonroy | Joint judicial appointment to complete an unexpired elected term |
| Tax Assessor-Collector | Bob Reeves | Election |
| County Treasurer | Tracy Soldan | Election |

## District Clerk transition

Dawn Lantz retired with March 31, 2026 as her last day. Kerr County has two district courts, and Texas Government Code § 51.301 assigns a District Clerk vacancy to the district judges acting by agreement. The 198th District Judge M. Patrick Maguire and 216th District Judge Albert D. Pattillo III jointly selected Eunavae Baublit Tonroy to complete the unexpired term.

The office remains a four-year elected District Clerk office. The appointment is a current-holder selection method; it does not create a second office, a new geography, or a vacancy record. The current District Clerk page uses the shorter public form Eunavae Baublit. The Elections campaign-finance table still names Dawn Lantz and is retained as stale transition evidence.

## County Clerk transition boundary

Nadene Alford was appointed by Commissioners Court in May 2024, but the county announcement expressly limited that appointment to December 31, 2024. The current office page and state election-administration directory identify Alford as the current County Clerk after that expiration. The expired 2024 appointment is retained as historical evidence and does not cause the current service to be counted as a second appointed holder.

## Geometry

The Elections page links the official Commissioner precinct map. The resolved ArcGIS feature service is:

`https://services1.arcgis.com/Ijqs2ihddUy84otW/ArcGIS/rest/services/Kerr_County_Commissioner_Precincts_2022/FeatureServer/0`

Layer contract:

- polygon layer 0
- stable district field `precinct`
- values `1` through `4`
- Court Order `39047`
- order date November 3, 2021
- effective date January 1, 2022
- ArcGIS service item `de7c8e02045a4981a752998bb6406538`

The countywide feature is the current TIGERweb county boundary for GEOID `48265`.

## QA result

- Current-officeholder evidence rows: 10
- Current holders selected by election: 9
- Current judicially appointed holders of elected offices: 1
- Duplicate District Clerk offices or holders: 0
- Explicit non-scope County Surveyor record: 1
- Normalized geography rows: 5
- Canonical geometry features: 5
- Countywide features: 1
- Commissioner-precinct features: 4
- Missing joins: 0
- Extra joins: 0
- `qa_status = approved`
- `parity_ok = TRUE`
- Combined canonical SHA-256: `c55276bef1b02f6f0de42f000e20f0218a7ee83b4ea95f0304ea921ddbfa5a4c`
