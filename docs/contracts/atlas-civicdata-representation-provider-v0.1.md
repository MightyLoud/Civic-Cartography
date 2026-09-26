# Atlas ↔ CivicData Representation Provider v0.1

Status: **interface implemented; live provider activation disabled**

## Purpose

Allow Civic Cartography's Atlas address resolver to consume certified representation
from the canonical civic-data layer without copying roster/identity authority into Atlas.

```text
Atlas address resolver
      |
      | lat + lon only
      v
location-aware representation provider
      |
      v
CivicData certified representation / snapshot manifest
```

## Boundary

Atlas owns address resolution, service-area routing, and civic issue routing.

CivicData owns the canonical representation/evidence contracts used by this interface:
jurisdiction/division identity, Organization/Person shared identity, Posts, Memberships,
certification, and snapshot provenance.

The interface is read-only. `canonical_writes` must equal `0`.

## Activation

The provider is disabled unless:

```text
ATLAS_REPRESENTATION_PROVIDER_URL
```

is set. The CSV endpoint does not call the provider. JSON enrichment is therefore
additive and cannot change the Google Sheets `IMPORTDATA` contract.

No live URL should be configured until a governed Colorado Springs / El Paso
location-aware representation source exists.

## Request

Atlas sends only:

```text
lat
lon
```

The typed and matched street address are not forwarded.

## PASS response

```text
schema_version = atlas-representation-provider/0.1
status = PASS
source_system
snapshot_manifest_sha256
jurisdiction_ocdid
division_ocdids[]
certification
offices[]
canonical_writes = 0
```

Each office carries Post/role/division identity, seat capacity, vacancy count,
current holders, and optional reviewed shared Organization/Person IDs.

## Fail-closed controls

Atlas rejects:

- uncertified representation;
- invalid OCDIDs;
- malformed shared `org-…` / `per-…` IDs;
- duplicate Posts or holders;
- seat/vacancy parity failures;
- invalid snapshot-manifest hashes;
- provider claims of canonical writes;
- malformed response shape.

Transport errors return `UNAVAILABLE`.
A valid provider may return `NO_APPLICABLE_REPRESENTATION`.

## Non-goals

This contract does not:

- infer civic facts from Atlas service-provider IDs;
- make Atlas a representation authority;
- enable partner write-back;
- activate a Colorado Springs roster before governed source data exists;
- modify existing service or issue routing.
