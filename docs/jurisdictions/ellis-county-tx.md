# Ellis County, Texas — Combined County and District Attorney

## Release scope

Ellis County is modeled as a bounded 11-office county release:

- County Judge — John Wray
- Commissioner Precinct 1 — Randy Stinson
- Commissioner Precinct 2 — Lane Grayson
- Commissioner Precinct 3 — Louis Ponder
- Commissioner Precinct 4 — Kyle Butler
- Sheriff — Brad Norman
- County and District Attorney — Lindy Beaty
- County Clerk — Krystal Valdez
- District Clerk — Melanie Reed
- Tax Assessor-Collector — Richard Rozier
- County Treasurer — Cheryl Chambers

County courts, district courts, justices of the peace, constables, the County Auditor, appraisal-district directors, Elections Administrator, emergency-services-district directors, and other judicial or appointed offices remain explicit non-scope evidence.

## Combined-prosecutor structure

Ellis County publishes Lindy Beaty as **County and District Attorney**. The office prosecutes felony, misdemeanor, and juvenile cases and provides legal advice to county officials. The release therefore contains:

- exactly one County and District Attorney office;
- exactly one current prosecutor officeholder;
- zero separate County Attorney rows;
- zero separate District Attorney rows; and
- zero Criminal District Attorney rows.

This is distinct from a consolidated Criminal District Attorney and from a county that elects separate County Attorney and District Attorney offices.

## County Judge transition

Commissioners Court appointed John Wray on May 7, 2025. He assumed office May 15, 2025 and serves the remainder of the term through the November 2026 election. His roster row therefore uses `selection_method = appointment`; the other ten scoped offices use `selection_method = election`.

## Commissioner geography

Ellis County's county-owned ArcGIS Enterprise Web Map identifies current MapServer layer `680`, **Commissioner Precincts (2023-2032)**. Field `Commissioner_Pct` controls precinct identity.

The source contract preserves:

- Web Map item `05e4901568c044819986934e3715b292`;
- Map Service item `484f13cc3dc64f20a64f5528ef79e035`;
- four publishable polygons labeled `1` through `4`;
- explicit exclusion of geometryless service-maintenance records;
- November 30, 2021 adoption; and
- January 1, 2023 effective date.

## Canonical output

The release publishes one Census countywide feature for GEOID `48139`, four Commissioner-precinct features, five normalized geography rows, five canonical GeoJSON features, zero missing or extra joins, `qa_status = approved`, and `parity_ok = TRUE`.

Combined canonical SHA-256:

`__DIGEST__`
