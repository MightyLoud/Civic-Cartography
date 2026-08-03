# Kaufman County, Texas

Kaufman County is modeled as an eleven-office county release with one countywide geography and four Commissioner-precinct geographies.

## Prosecutor consolidation

The elected Criminal District Attorney is one office. Texas Government Code § 44.229 assigns the Kaufman County Criminal District Attorney the duties otherwise conferred on county and district attorneys. The county publishes Erleigh Norville Wiley as the elected Criminal District Attorney and routes both criminal prosecution and Civil Division/public-information functions through that office.

The release therefore does not create separate County Attorney or District Attorney rows, vacancies, officeholders, or geometries.

## Current bounded scope

- County Judge
- Commissioner Precincts 1–4
- Sheriff
- County Clerk
- District Clerk
- Tax Assessor-Collector
- County Treasurer
- Criminal District Attorney

County Surveyor, constables, justices of the peace, county courts, and district courts remain explicit non-scope evidence.

## Naming contracts

- `William “Skeet” Phillips` preserves the official Commissioners Court form `Skeet Phillips` and the current campaign-finance form `William Phillips` as one person.
- `Jakie Allen` follows the current County Judge and Commissioners Court pages; campaign-finance spelling variants do not override the office page.
- `Teressa Floyd` follows the current Tax Assessor page; the isolated `Teresa Floyd` campaign-finance spelling is non-controlling.
- `Charles “Chuck” Mohnkern` preserves the office-page and campaign-finance name forms as one person.

## Geography

The countywide feature is the current Census TIGERweb county polygon for GEOID `48257`. Commissioner geometry is resolved from the official county-linked ArcGIS application `da2d7bb2339b4c67bfe382fc24bb775a`; the committed source contract pins the controlling polygon layer, stable district field, values 1–4, and source attributes.

## Definition of done

The release is complete only when raw evidence, normalized data, live-source validation, canonical GeoJSON, zero missing/extra joins, `qa_status = approved`, `parity_ok = TRUE`, final-head CI, and the Command Center portfolio row all agree.
