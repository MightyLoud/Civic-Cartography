# Burnet County, Texas

## Release model

Burnet County is the separate-prosecutor geography template. The bounded release contains twelve current elected offices across six geometries:

- one Burnet Countywide geography;
- four Burnet County Commissioner precincts; and
- one District Attorney service area spanning Blanco, Burnet, Llano, and San Saba Counties.

## Current elected offices

| Office | Current holder | Geography |
|---|---|---|
| County Judge | Bryan Wilson | Burnet County |
| Commissioner Precinct 1 | Jim Luther, Jr. | Commissioner Precinct 1 |
| Commissioner Precinct 2 | Damon Beierle | Commissioner Precinct 2 |
| Commissioner Precinct 3 | Chad Collier | Commissioner Precinct 3 |
| Commissioner Precinct 4 | Joe Don Dockery | Commissioner Precinct 4 |
| Sheriff | Calvin Boyd | Burnet County |
| County Clerk | Vicinta Stafford | Burnet County |
| District Clerk | Casie Walker | Burnet County |
| Tax Assessor-Collector | DeAnne Fisher | Burnet County |
| County Treasurer | Karrie Crownover | Burnet County |
| County Attorney | Eddie Arredondo | Burnet County |
| District Attorney, 33rd & 424th Judicial Districts | Perry Thomas | Blanco, Burnet, Llano, and San Saba Counties |

## Prosecutor separation

The County Attorney and District Attorney are two current elected offices, with two holders and two service geographies.

- **County Attorney:** Eddie Arredondo; Burnet Countywide geography.
- **District Attorney:** Perry Thomas; four-county geography for the 33rd and 424th Judicial Districts.
- **Criminal District Attorney:** no row is created.

The official county expunction guidance lists the Burnet County Attorney and the 33rd/424th District Attorney as separate agencies. The District Attorney's geometry is the exact union of current Census boundaries for Blanco (`48031`), Burnet (`48053`), Llano (`48299`), and San Saba (`48411`) Counties.

## Commissioner geometry

The county-linked ArcGIS application is the geometry entrypoint. The permanent source contract records the resolved operational layer, stable district field, source feature count, and the deterministic dissolve into four Commissioner precincts.

## Scope exclusions

County Court at Law, district judges, Justices of the Peace, constables, magistrates, and the North Hill Country Public Defender remain explicit source evidence but are not inserted into this bounded release.

## QA contract

- 12 current officeholder rows
- 12 scoped elected offices
- 12 unique current officeholders
- 1 County Attorney
- 1 District Attorney
- 0 Criminal District Attorneys
- 6 normalized geography rows
- 6 canonical geometry features
- 0 missing joins
- 0 extra joins
- `qa_status = approved`
- `parity_ok = TRUE`
