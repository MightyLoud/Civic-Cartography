from __future__ import annotations

from pathlib import Path

import pytest

from civic_cartography.authoritative_overrides import (
    AuthoritativeOverrideError,
    load_authoritative_overrides,
    resolve_authoritative_override,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "data" / "authoritative_jurisdiction_overrides.yml"


def test_rtd_override_resolves_only_exact_maintained_aliases() -> None:
    overrides = load_authoritative_overrides(REGISTRY)

    canonical = resolve_authoritative_override(
        overrides, state="co", name="Regional Transportation District"
    )
    abbreviation = resolve_authoritative_override(
        overrides, state="CO", name="RTD"
    )
    near_miss = resolve_authoritative_override(
        overrides, state="co", name="Regional Transit District"
    )

    assert canonical is not None
    assert canonical.override_id == "co-regional-transportation-district"
    assert canonical.ocdid == (
        "ocd-division/country:us/state:co/"
        "special_district:regional_transportation_district"
    )
    assert canonical.generator_override["classification"] == "transit_authority"
    assert abbreviation == canonical
    assert near_miss is None


def test_discovery_overrides_resolve_exact_reviewed_aliases() -> None:
    overrides = load_authoritative_overrides(REGISTRY)

    bart = resolve_authoritative_override(
        overrides, state="ca", name="Bay Area Rapid Transit District"
    )
    mwrd = resolve_authoritative_override(
        overrides,
        state="IL",
        name="Metropolitan Water Reclamation District of Greater Chicago",
    )
    port = resolve_authoritative_override(
        overrides, state="wa", name="Port of Seattle"
    )

    assert bart is not None
    assert bart.override_id == (
        "ca-san-francisco-bay-area-rapid-transit-district"
    )
    assert bart.ocdid == (
        "ocd-division/country:us/state:ca/special_district:"
        "san_francisco_bay_area_rapid_transit_district"
    )
    assert bart.generator_override["classification"] == "transit_authority"

    assert mwrd is not None
    assert mwrd.override_id == "il-metropolitan-water-reclamation-district"
    assert mwrd.ocdid == "ocd-division/country:us/state:il/sewer:mwrd"
    assert mwrd.generator_override["classification"] == "special_purpose_district"

    assert port is not None
    assert port.override_id == "wa-port-of-seattle"
    assert port.ocdid == (
        "ocd-division/country:us/state:wa/special_district:port_of_seattle"
    )
    assert port.generator_override["classification"] == "special_purpose_district"

    assert (
        resolve_authoritative_override(
            overrides, state="ca", name="Bay Area Regional Transit District"
        )
        is None
    )
    assert (
        resolve_authoritative_override(
            overrides, state="wa", name="Port of Tacoma"
        )
        is None
    )


def test_override_registry_rejects_duplicate_aliases(tmp_path: Path) -> None:
    path = tmp_path / "overrides.yml"
    path.write_text(
        """version: 1
overrides:
  - override_id: first
    state: co
    canonical_name: Example District
    aliases: [Example District]
    ocdid: ocd-division/country:us/state:co/special_district:example
    jurisdiction:
      has_jurisdiction: true
      classification: transit_authority
      jurisdiction_name: Example District
      jurisdiction_type_suffix: transit_authority
      url: https://example.com/
    source:
      source_name: Example
      source_url: {official: https://example.com/}
      source_description: Example source
    verified_asof: '2026-08-02'
    evidence_notes: Example evidence
  - override_id: second
    state: co
    canonical_name: Example District
    aliases: [Example District]
    ocdid: ocd-division/country:us/state:co/special_district:example_two
    jurisdiction:
      has_jurisdiction: true
      classification: transit_authority
      jurisdiction_name: Example District
      jurisdiction_type_suffix: transit_authority
      url: https://example.com/
    source:
      source_name: Example
      source_url: {official: https://example.com/}
      source_description: Example source
    verified_asof: '2026-08-02'
    evidence_notes: Example evidence
""",
        encoding="utf-8",
    )

    with pytest.raises(AuthoritativeOverrideError, match="duplicate state/name"):
        load_authoritative_overrides(path)


def test_castaic_lake_water_agency_resolves_to_current_successor() -> None:
    overrides = load_authoritative_overrides(REGISTRY)

    legacy = resolve_authoritative_override(
        overrides, state="ca", name="Castaic Lake Water Agency"
    )
    current = resolve_authoritative_override(
        overrides, state="CA", name="Santa Clarita Valley Water Agency"
    )

    assert legacy is not None
    assert legacy == current
    assert legacy.override_id == "ca-santa-clarita-valley-water-agency-successor"
    assert legacy.ocdid == (
        "ocd-division/country:us/state:ca/county:los_angeles/"
        "water:castaic_lake_water_agency"
    )
    assert legacy.generator_override["jurisdiction_name"] == (
        "Santa Clarita Valley Water Agency"
    )
    assert legacy.generator_override["classification"] == "special_purpose_district"

