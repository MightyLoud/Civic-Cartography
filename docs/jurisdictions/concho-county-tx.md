# Concho County, Texas — Dual Combined Offices

## Release scope

Concho County is modeled as a bounded eight-office county release:

- County Judge — David Dillard
- Commissioner Precinct 1 — Trey Bradshaw
- Commissioner Precinct 2 — Eric Gully
- Commissioner Precinct 3 — Chad Miller
- Commissioner Precinct 4 — Keith Dillard
- Sheriff/Tax Assessor-Collector — Brent Frazier
- County/District Clerk — Amber Hall
- County Treasurer — Jenifer Gierisch

County Attorney, District Attorney, district judge, justice of the peace, constable, and other judicial or appointed offices remain explicit non-scope evidence.

## Dual combined-office structure

Concho County publishes Brent Frazier as County Sheriff/Tax Assessor-Collector and Amber Hall as County/District Clerk. The release contains exactly one row for each combined office and zero separate component-office rows.

Texas Constitution Article VIII §14 makes the sheriff the assessor-collector in a county under 10,000 inhabitants unless county voters create a separate assessor-collector office. Texas Constitution Article V §20 permits a single elected clerk to perform both district- and county-clerk duties in a small county.

The Texas Secretary of State tax-assessor directory still lists former holder Chad Miller. That stale record is retained in the source manifest rather than silently discarded. Current county campaign-finance filings, the county Sheriff and Tax Assessor pages, TxDMV, and the Comptroller identify Brent Frazier.

## Commissioner geography

Concho County's official 2021 VTD plan labels eight current voting precincts inside the four Commissioner precincts. The current Texas Legislative Council `Precincts26P` polygons provide exact geometry.

The three-digit voting precinct IDs encode Commissioner identity in the hundreds digit:

- Commissioner Precinct 1: `101`, `102`
- Commissioner Precinct 2: `203`, `204`, `205`
- Commissioner Precinct 3: `306`
- Commissioner Precinct 4: `407`, `408`

The maintained derivation enforces all eight IDs, dissolves them into four nonempty Commissioner features, and requires zero overlap and zero difference from the source voting-precinct union.

## Canonical output

The release publishes one Census countywide feature for GEOID `48095`, four Commissioner-precinct features, five normalized geography rows, five canonical GeoJSON features, zero missing or extra joins, `qa_status = approved`, and `parity_ok = TRUE`.

Combined canonical SHA-256:

`__DIGEST__`
