from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from civic_cartography.target_manifest import SUPPORTED_CLASSIFICATIONS


class CanonicalAliasError(ValueError):
    """Raised when a maintained canonical alias registry is invalid."""


@dataclass(frozen=True)
class CanonicalAlias:
    alias_id: str
    state: str
    canonical_name: str
    members: tuple[str, ...]
    canonical_member: str
    classification: str
    jurisdiction_name: str
    url: str
    source: dict[str, Any]
    verified_asof: str
    evidence_notes: str
    member_display_names: dict[str, str]

    @property
    def canonical_jurisdiction_ocdid(self) -> str:
        division_part = self.canonical_member.removeprefix("ocd-division/")
        return f"ocd-jurisdiction/{division_part}/{self.classification}"

    @property
    def generator_override(self) -> dict[str, Any]:
        return {
            "has_jurisdiction": True,
            "classification": self.classification,
            "jurisdiction_name": self.jurisdiction_name,
            "jurisdiction_type_suffix": self.classification,
            "url": self.url,
        }

    @property
    def source_override(self) -> dict[str, Any]:
        return dict(self.source)

    def member_metadata(self, member: str) -> dict[str, Any]:
        if member not in self.members:
            raise CanonicalAliasError(
                f"{member} is not a member of canonical alias {self.alias_id}"
            )
        is_canonical = member == self.canonical_member
        metadata = {
            "_canonical_alias_id": self.alias_id,
            "_canonical_alias_is_canonical": is_canonical,
            "_canonical_alias_member": member,
            "_canonical_division_ocdid": self.canonical_member,
            "_canonical_jurisdiction_ocdid": self.canonical_jurisdiction_ocdid,
            "_suppress_jurisdiction_generation": not is_canonical,
        }
        display_name = self.member_display_names.get(member)
        if display_name is not None:
            metadata["_canonical_alias_member_display_name"] = display_name
        return metadata


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalAliasError(f"{location} must be a mapping")
    return dict(value)


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalAliasError(f"{location} must be a non-empty string")
    return value.strip()


def _normalize_ocdid(value: Any, state: str, location: str) -> str:
    ocdid = _require_string(value, location).rstrip("/")
    prefix = f"ocd-division/country:us/state:{state}/"
    if not ocdid.startswith(prefix):
        raise CanonicalAliasError(f"{location} must begin with {prefix}")
    return ocdid


def _parse_alias(raw: Any, index: int) -> CanonicalAlias:
    location = f"aliases[{index}]"
    item = _require_mapping(raw, location)
    required = {
        "alias_id",
        "state",
        "canonical_name",
        "members",
        "canonical_member",
        "classification",
        "jurisdiction_name",
        "url",
        "source",
        "verified_asof",
        "evidence_notes",
    }
    optional = {"member_display_names"}
    if not required.issubset(item) or set(item) - required - optional:
        missing = sorted(required - set(item))
        extra = sorted(set(item) - required - optional)
        raise CanonicalAliasError(
            f"{location} keys mismatch; missing={missing}, extra={extra}"
        )

    state = _require_string(item["state"], f"{location}.state").lower()
    if not re.fullmatch(r"[a-z]{2}", state):
        raise CanonicalAliasError(f"{location}.state must be two lowercase letters")

    raw_members = item["members"]
    if not isinstance(raw_members, list) or len(raw_members) < 2:
        raise CanonicalAliasError(f"{location}.members must contain at least two IDs")
    members = tuple(
        _normalize_ocdid(member, state, f"{location}.members[{member_index}]")
        for member_index, member in enumerate(raw_members)
    )
    if len(set(members)) != len(members):
        raise CanonicalAliasError(f"{location}.members must not contain duplicates")

    raw_member_display_names = item.get("member_display_names", {})
    member_display_name_map = _require_mapping(
        raw_member_display_names, f"{location}.member_display_names"
    )
    member_display_names: dict[str, str] = {}
    for raw_member, raw_display_name in member_display_name_map.items():
        member = _normalize_ocdid(
            raw_member, state, f"{location}.member_display_names key"
        )
        if member not in members:
            raise CanonicalAliasError(
                f"{location}.member_display_names keys must be maintained members"
            )
        member_display_names[member] = _require_string(
            raw_display_name, f"{location}.member_display_names.{member}"
        )

    canonical_member = _normalize_ocdid(
        item["canonical_member"], state, f"{location}.canonical_member"
    )
    if canonical_member not in members:
        raise CanonicalAliasError(
            f"{location}.canonical_member must be one of the maintained members"
        )

    classification = _require_string(
        item["classification"], f"{location}.classification"
    )
    if classification not in SUPPORTED_CLASSIFICATIONS:
        raise CanonicalAliasError(
            f"{location}.classification must be supported"
        )

    source = _require_mapping(item["source"], f"{location}.source")
    if set(source) != {"source_name", "source_url", "source_description"}:
        raise CanonicalAliasError(
            f"{location}.source must contain source_name, source_url, and source_description"
        )
    source["source_name"] = _require_string(
        source["source_name"], f"{location}.source.source_name"
    )
    source_urls = _require_mapping(
        source["source_url"], f"{location}.source.source_url"
    )
    if not source_urls:
        raise CanonicalAliasError(f"{location}.source.source_url must not be empty")
    source["source_url"] = {
        _require_string(key, f"{location}.source.source_url key"): _require_string(
            value, f"{location}.source.source_url.{key}"
        )
        for key, value in source_urls.items()
    }
    source["source_description"] = _require_string(
        source["source_description"], f"{location}.source.source_description"
    )

    return CanonicalAlias(
        alias_id=_require_string(item["alias_id"], f"{location}.alias_id"),
        state=state,
        canonical_name=_require_string(
            item["canonical_name"], f"{location}.canonical_name"
        ),
        members=members,
        canonical_member=canonical_member,
        classification=classification,
        jurisdiction_name=_require_string(
            item["jurisdiction_name"], f"{location}.jurisdiction_name"
        ),
        url=_require_string(item["url"], f"{location}.url"),
        source=source,
        verified_asof=_require_string(
            item["verified_asof"], f"{location}.verified_asof"
        ),
        evidence_notes=_require_string(
            item["evidence_notes"], f"{location}.evidence_notes"
        ),
        member_display_names=member_display_names,
    )


def load_canonical_aliases(path: str | Path) -> tuple[CanonicalAlias, ...]:
    registry_path = Path(path)
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CanonicalAliasError(f"canonical alias registry not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise CanonicalAliasError(
            f"canonical alias registry is invalid YAML: {path}"
        ) from exc

    root = _require_mapping(raw, "registry")
    if set(root) != {"version", "aliases"} or root["version"] != 1:
        raise CanonicalAliasError(
            "canonical alias registry must contain version: 1 and aliases"
        )
    raw_aliases = root["aliases"]
    if not isinstance(raw_aliases, list) or not raw_aliases:
        raise CanonicalAliasError("canonical alias registry must contain aliases")

    aliases = tuple(_parse_alias(item, index) for index, item in enumerate(raw_aliases))
    seen_ids: set[str] = set()
    seen_member_sets: set[tuple[str, frozenset[str]]] = set()
    for alias in aliases:
        if alias.alias_id in seen_ids:
            raise CanonicalAliasError(f"duplicate alias_id: {alias.alias_id}")
        seen_ids.add(alias.alias_id)
        key = (alias.state, frozenset(alias.members))
        if key in seen_member_sets:
            raise CanonicalAliasError(
                f"duplicate canonical alias member set for state {alias.state}"
            )
        seen_member_sets.add(key)
    return aliases


def resolve_canonical_alias(
    aliases: tuple[CanonicalAlias, ...], *, state: str, members: list[str] | tuple[str, ...]
) -> CanonicalAlias | None:
    key = (state.lower(), frozenset(member.rstrip("/") for member in members))
    for alias in aliases:
        if key == (alias.state, frozenset(alias.members)):
            return alias
    return None


def canonical_alias_to_dict(alias: CanonicalAlias) -> Mapping[str, Any]:
    return {
        "alias_id": alias.alias_id,
        "state": alias.state,
        "canonical_name": alias.canonical_name,
        "members": list(alias.members),
        "canonical_member": alias.canonical_member,
        "canonical_jurisdiction_ocdid": alias.canonical_jurisdiction_ocdid,
        "classification": alias.classification,
        "jurisdiction_name": alias.jurisdiction_name,
        "url": alias.url,
        "source": dict(alias.source),
        "verified_asof": alias.verified_asof,
        "evidence_notes": alias.evidence_notes,
        "member_display_names": dict(alias.member_display_names),
    }
