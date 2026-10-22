# Schleicher County, Texas — Combined County and District Clerk

## Release scope

Schleicher County is modeled as a bounded nine-office county release:

- County Judge — Charlie Bradley
- Commissioner Precinct 1 — Gary Gibson
- Commissioner Precinct 2 — Steve Nelson
- Commissioner Precinct 3 — Kirk Griffin
- Commissioner Precinct 4 — Chris Meador
- Sheriff — Jason Chatham
- County and District Clerk — Marsha L. Maskill
- Tax Assessor-Collector — Vanessa Covarrubiaz
- County Treasurer — Cassandra Buitron

County Attorney, District Attorney, district judge, justice of the peace, constable, and other court or appointed offices remain explicit non-scope evidence.

The County Treasurer page was refreshed on August 13, 2026. It identifies Cassandra Buitron, replacing the previously retained Jennifer L. Henderson record. The page does not establish a succession date, election event, or reason for the change, so none is inferred.

## Combined-clerk structure

Schleicher County publishes Marsha L. Maskill as **County and District Clerk** on its County Clerk, District Clerk, and Elections pages. The release therefore contains:

- exactly one combined clerk office;
- exactly one current clerk officeholder;
- zero separate County Clerk rows; and
- zero separate District Clerk rows.

Texas Constitution Article V §20 permits a county with fewer than 8,000 residents to elect a single clerk who performs both District Clerk and County Clerk duties. The Texas Secretary of State's 2026 qualifications guide separately lists “District & County Clerk” as one elected four-year office.

## Commissioner geography

The maintained derivation combines three official current or adopted authorities:

1. Schleicher County's November 1, 2021 adoption order controls Commissioner precinct identity.
2. Schleicher County's 2024 primary-precinct map confirms the current four-number precinct layout.
3. The Texas Legislative Council's current `Precincts26P` polygons control exact geometry.

The adopted order's full-county Commissioner map is rendered at a fixed size. Multiple interior samples from each current TLC polygon are classified against the adopted map's pinned precinct colors. Each current voting precinct independently resolves to the Commissioner precinct with the same number.

Confirmed geometry:

- 4/4 current voting precincts assigned;
- 4 nonempty Commissioner precincts;
- minimum assignment confidence: `0.87`;
- mean assignment confidence: `0.939899`;
- interdistrict overlap: `0`;
- source-union symmetric difference: `0`;
- one current voting precinct per Commissioner precinct.

## Canonical output

The release publishes:

- one Census countywide feature for GEOID `48413`;
- four Commissioner-precinct features;
- five normalized geography rows;
- five canonical GeoJSON features;
- zero missing or extra geometry joins;
- `qa_status = approved`; and
- `parity_ok = TRUE`.

The dedicated workflow regenerates both countywide and Commissioner geometry from the pinned authorities and compares the resulting snapshots before publication.

Combined canonical SHA-256:

`70575f6d635746024f155eb2598c9551a58a96fa6fa9e90b050bbb17702fd3bf`
