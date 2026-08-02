# RTD authoritative jurisdiction override

## Problem

The Regional Transportation District fixture cannot resolve from the current
Open Civic Data master/local identifier inputs. The target is nevertheless a
real Colorado public body with a state-created statutory identity and an elected
board.

Free-text fuzzy matching is not acceptable for creating a new identifier.
Handcrafted output YAML is also not acceptable.

## Decision

Maintain a reviewed authoritative override in
`data/authoritative_jurisdiction_overrides.yml`.

The RTD record defines:

- canonical name and exact aliases;
- state;
- stable OCD division ID;
- Jurisdiction classification and name;
- official URL;
- official-source provenance;
- verification date; and
- evidence notes explaining why the override exists.

The maintained division ID is:

`ocd-division/country:us/state:co/special_district:regional_transportation_district`

The generated Jurisdiction ID is:

`ocd-jurisdiction/country:us/state:co/special_district:regional_transportation_district/transit_authority`

## Resolution rules

- Overrides resolve only by exact normalized state/name aliases.
- No fuzzy matching is used.
- Near-miss names remain unresolved.
- Override candidates enter the normal upstream ingest and generation pipeline.
- The generator creates the Division and Jurisdiction YAML; the adapter does not
  handcraft either artifact.

## Upstream patch behavior

Patch 3 exposes the existing `infer_jurisdiction_seed(exact_override=...)` hook
through generation requests and embedded ingest metadata. It also:

- uses the authoritative name for a no-validation-match stub Division;
- uses official-source provenance for Division and Jurisdiction sourcing;
- uses the official jurisdiction URL;
- sets the Division's `jurisdiction_id` after classification, preventing a
  hardcoded `/government` reference for transit authorities; and
- preserves the upstream partial response when validation enrichment is absent.

## Evidence basis

Official RTD materials state that Colorado created RTD under the Regional
Transportation District Act, C.R.S. 32-9-101 et seq., and describe it as a
public body responsible for developing, maintaining, and operating the regional
mass-transit system. RTD governance materials identify the elected board and the
Act governing the district.

## Expected gate movement

The honest expected result is 5/6:

- Seattle: pass
- Tacoma: pass
- Pierce County: pass
- Colorado Springs School District 11: pass
- Regional Transportation District: pass through the authoritative override
- City and County of Denver: remain failed until alias canonicalization is solved

RTD remains partial for validation enrichment, but complete for artifact
generation and classification.
