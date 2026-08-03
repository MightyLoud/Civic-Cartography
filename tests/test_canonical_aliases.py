from __future__ import annotations

from pathlib import Path

import pytest

from civic_cartography.canonical_aliases import (
    CanonicalAliasError,
    load_canonical_aliases,
    resolve_canonical_alias,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "data" / "canonical_alias_groups.yml"
PLACE = "ocd-division/country:us/state:co/place:denver"
COUNTY = "ocd-division/country:us/state:co/county:denver"
JURISDICTION = "ocd-jurisdiction/country:us/state:co/place:denver/government"
NASHVILLE_PLACE = "ocd-division/country:us/state:tn/place:nashville"
DAVIDSON_COUNTY = "ocd-division/country:us/state:tn/county:davidson"
NASHVILLE_JURISDICTION = (
    "ocd-jurisdiction/country:us/state:tn/county:davidson/government"
)


def test_denver_alias_resolves_exact_member_set_order_independently() -> None:
    aliases = load_canonical_aliases(REGISTRY)
    alias = resolve_canonical_alias(
        aliases,
        state="CO",
        members=[COUNTY, PLACE],
    )
    incomplete = resolve_canonical_alias(
        aliases,
        state="co",
        members=[PLACE],
    )

    assert alias is not None
    assert alias.alias_id == "co-denver-consolidated-city-county"
    assert alias.canonical_member == PLACE
    assert alias.canonical_jurisdiction_ocdid == JURISDICTION
    assert alias.generator_override["classification"] == "government"
    assert incomplete is None


def test_alias_member_metadata_suppresses_only_secondary_member() -> None:
    alias = load_canonical_aliases(REGISTRY)[0]

    canonical = alias.member_metadata(PLACE)
    secondary = alias.member_metadata(COUNTY)

    assert canonical["_canonical_alias_is_canonical"] is True
    assert canonical["_suppress_jurisdiction_generation"] is False
    assert canonical["_canonical_jurisdiction_ocdid"] == JURISDICTION
    assert secondary["_canonical_alias_is_canonical"] is False
    assert secondary["_suppress_jurisdiction_generation"] is True
    assert secondary["_canonical_jurisdiction_ocdid"] == JURISDICTION



def test_nashville_davidson_alias_prefers_county_government_root() -> None:
    aliases = load_canonical_aliases(REGISTRY)
    alias = resolve_canonical_alias(
        aliases,
        state="TN",
        members=[NASHVILLE_PLACE, DAVIDSON_COUNTY],
    )

    assert alias is not None
    assert alias.alias_id == "tn-nashville-davidson-metropolitan-government"
    assert alias.canonical_member == DAVIDSON_COUNTY
    assert alias.canonical_jurisdiction_ocdid == NASHVILLE_JURISDICTION
    assert alias.generator_override["classification"] == "government"
    assert alias.member_metadata(DAVIDSON_COUNTY)[
        "_suppress_jurisdiction_generation"
    ] is False
    assert alias.member_metadata(NASHVILLE_PLACE)[
        "_suppress_jurisdiction_generation"
    ] is True


def test_alias_registry_rejects_canonical_member_outside_group(tmp_path: Path) -> None:
    path = tmp_path / "aliases.yml"
    path.write_text(
        """version: 1
aliases:
  - alias_id: invalid
    state: co
    canonical_name: Example
    members:
      - ocd-division/country:us/state:co/place:example
      - ocd-division/country:us/state:co/county:example
    canonical_member: ocd-division/country:us/state:co/place:other
    classification: government
    jurisdiction_name: Example Government
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

    with pytest.raises(CanonicalAliasError, match="canonical_member"):
        load_canonical_aliases(path)
