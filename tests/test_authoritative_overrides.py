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


def test_denver_county_1_override_resolves_exact_official_aliases() -> None:
    overrides = load_authoritative_overrides(REGISTRY)

    cde_name = resolve_authoritative_override(
        overrides, state="co", name="Denver County 1"
    )
    public_name = resolve_authoritative_override(
        overrides, state="CO", name="Denver Public Schools"
    )
    manifest_name = resolve_authoritative_override(
        overrides,
        state="co",
        name="School District No. 1 in the City and County of Denver",
    )
    near_miss = resolve_authoritative_override(
        overrides, state="co", name="Denver County School District"
    )

    assert cde_name is not None
    assert cde_name.override_id == "co-denver-county-1"
    assert cde_name.canonical_name == "Denver County 1"
    assert cde_name.ocdid == (
        "ocd-division/country:us/state:co/"
        "school_district:denver_county_1"
    )
    assert cde_name.generator_override == {
        "has_jurisdiction": True,
        "classification": "school_system",
        "jurisdiction_name": "Denver Public Schools",
        "jurisdiction_type_suffix": "school_system",
        "url": "https://www.dpsk12.org/",
    }
    assert cde_name.source_override["source_url"]["cde_district_profile"].endswith(
        "/0880"
    )
    assert "0880" in cde_name.evidence_notes
    assert public_name == cde_name
    assert manifest_name == cde_name
    assert near_miss is None


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
