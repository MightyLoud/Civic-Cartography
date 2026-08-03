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

## Authoritative composite geometry

The official county GIS application is retained as the public map entrypoint, but `gis.kaufmancounty.net` resolved to `67.133.180.13` and timed out before any HTTP response from GitHub-hosted runners. The release does not silently substitute an unrelated public ArcGIS item.

Instead, the maintained derivation uses two authoritative components:

1. Kaufman County's pinned official Commissioner map controls the assignment of territory to Precincts 1–4. The 940×788 PNG has SHA-256 `49673d66657b8dd93daec7aad205d549023bffa263c5db71707032ae321ca8e6`.
2. The Texas Legislative Council's July 15, 2026 `Precincts26P` shapefile controls exact polygon geometry. Its ZIP has SHA-256 `70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107`.

The script georeferences the official PNG to the Kaufman voting-precinct union in Web Mercator, classifies multiple interior samples from every voting precinct by nearest pinned Commissioner color, and dissolves the 37 voting precincts by majority assignment. The county's November and December 2021 final redistricting actions establish that election precinct boundaries must conform to the Commissioner precincts.

Validation requires:

- all 37 voting precincts assigned;
- four nonempty Commissioner groups;
- minimum assignment confidence at least 0.60;
- mean assignment confidence at least 0.90;
- zero interdistrict overlap;
- exact equality between the dissolved Commissioner union and the source voting-precinct union;
- byte-identical regeneration from current pinned sources.

The confirmed assignment has mean confidence `0.926576`, minimum confidence `0.633333`, zero overlap, and zero union difference. The countywide feature is the current Census TIGERweb county polygon for GEOID `48257`.

## Definition of done

The release is complete only when raw evidence, normalized data, live-source validation, canonical GeoJSON, zero missing/extra joins, `qa_status = approved`, `parity_ok = TRUE`, final-head CI, and the Command Center portfolio row all agree.
