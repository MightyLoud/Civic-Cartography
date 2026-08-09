from __future__ import annotations

from pathlib import Path

from civic_cartography.canonical_aliases import (
    load_canonical_aliases,
    resolve_canonical_alias,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "data" / "canonical_alias_groups.yml"
RICHMOND_PLACE = "ocd-division/country:us/state:va/place:richmond"
RICHMOND_CITY_COUNTY_EQUIVALENT = (
    "ocd-division/country:us/state:va/county:richmond_city"
)
RICHMOND_COUNTY = "ocd-division/country:us/state:va/county:richmond"
RICHMOND_JURISDICTION = (
    "ocd-jurisdiction/country:us/state:va/place:richmond/government"
)


def test_richmond_independent_city_alias_prefers_place_government_root() -> None:
    aliases = load_canonical_aliases(REGISTRY)
    alias = resolve_canonical_alias(
        aliases,
        state="VA",
        members=[RICHMOND_PLACE, RICHMOND_CITY_COUNTY_EQUIVALENT],
    )
    incomplete = resolve_canonical_alias(
        aliases,
        state="va",
        members=[RICHMOND_PLACE],
    )
    richmond_county_pair = resolve_canonical_alias(
        aliases,
        state="va",
        members=[RICHMOND_PLACE, RICHMOND_COUNTY],
    )

    assert alias is not None
    assert alias.alias_id == "va-richmond-independent-city"
    assert alias.canonical_member == RICHMOND_PLACE
    assert alias.canonical_jurisdiction_ocdid == RICHMOND_JURISDICTION
    assert alias.jurisdiction_name == "Richmond"
    assert alias.generator_override["classification"] == "government"
    assert alias.member_metadata(RICHMOND_PLACE)[
        "_suppress_jurisdiction_generation"
    ] is False
    assert alias.member_metadata(RICHMOND_CITY_COUNTY_EQUIVALENT)[
        "_suppress_jurisdiction_generation"
    ] is True
    assert alias.member_metadata(RICHMOND_CITY_COUNTY_EQUIVALENT)[
        "_canonical_jurisdiction_ocdid"
    ] == RICHMOND_JURISDICTION
    assert incomplete is None
    assert richmond_county_pair is None
