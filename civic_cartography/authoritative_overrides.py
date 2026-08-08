from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from civic_cartography.target_manifest import SUPPORTED_CLASSIFICATIONS


class AuthoritativeOverrideError(ValueError):
    """Raised when the maintained override registry is invalid."""


@dataclass(frozen=True)
class AuthoritativeOverride:
    override_id: str
    state: str
    canonical_name: str
    aliases: tuple[str, ...]
    ocdid: str
    validation_geoid: str | None
    jurisdiction: dict[str, Any]
    source: dict[str, Any]
    verified_asof: str
    evidence_notes: str

    @property
    def generator_override(self) -> dict[str, Any]:
        override = dict(self.jurisdiction)
        if self.validation_geoid is not None:
            override["validation_geoid"] = self.validation_geoid
        return override

    @property
    def source_override(self) -> dict[str, Any]:
        return dict(self.source)


def normalize_override_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthoritativeOverrideError(f"{location} must be a mapping")
    return dict(value)


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthoritativeOverrideError(f"{location} must be a non-empty string")
    return value.strip()


def _parse_override(raw: Any, index: int) -> AuthoritativeOverride:
    location = f"overrides[{index}]"
    item = _require_mapping(raw, location)
    required = {
        "override_id",
        "state",
        "canonical_name",
        "aliases",
        "ocdid",
        "jurisdiction",
        "source",
        "verified_asof",
        "evidence_notes",
    }
    optional = {"validation_geoid"}
    if not required.issubset(item) or set(item) - required - optional:
        missing = sorted(required - set(item))
        extra = sorted(set(item) - required - optional)
        raise AuthoritativeOverrideError(
            f"{location} keys mismatch; missing={missing}, extra={extra}"
        )

    state = _require_string(item["state"], f"{location}.state").lower()
    if not re.fullmatch(r"[a-z]{2}", state):
        raise AuthoritativeOverrideError(f"{location}.state must be two lowercase letters")

    canonical_name = _require_string(
        item["canonical_name"], f"{location}.canonical_name"
    )
    aliases_raw = item["aliases"]
    if not isinstance(aliases_raw, list) or not aliases_raw:
        raise AuthoritativeOverrideError(f"{location}.aliases must be a non-empty list")
    aliases = tuple(
        _require_string(alias, f"{location}.aliases[{alias_index}]")
        for alias_index, alias in enumerate(aliases_raw)
    )
    if normalize_override_name(canonical_name) not in {
        normalize_override_name(alias) for alias in aliases
    }:
        raise AuthoritativeOverrideError(
            f"{location}.aliases must include the canonical name"
        )

    ocdid = _require_string(item["ocdid"], f"{location}.ocdid").rstrip("/")
    expected_prefix = f"ocd-division/country:us/state:{state}/"
    if not ocdid.startswith(expected_prefix):
        raise AuthoritativeOverrideError(
            f"{location}.ocdid must begin with {expected_prefix}"
        )

    validation_geoid = None
    if "validation_geoid" in item:
        validation_geoid = _require_string(
            item["validation_geoid"], f"{location}.validation_geoid"
        )
        if not re.fullmatch(r"[0-9]+", validation_geoid):
            raise AuthoritativeOverrideError(
                f"{location}.validation_geoid must contain only digits"
            )

    jurisdiction = _require_mapping(item["jurisdiction"], f"{location}.jurisdiction")
    jurisdiction_required = {
        "has_jurisdiction",
        "classification",
        "jurisdiction_name",
        "jurisdiction_type_suffix",
        "url",
    }
    if set(jurisdiction) != jurisdiction_required:
        raise AuthoritativeOverrideError(
            f"{location}.jurisdiction must contain exactly "
            f"{sorted(jurisdiction_required)}"
        )
    if jurisdiction["has_jurisdiction"] is not True:
        raise AuthoritativeOverrideError(
            f"{location}.jurisdiction.has_jurisdiction must be true"
        )
    classification = _require_string(
        jurisdiction["classification"], f"{location}.jurisdiction.classification"
    )
    if classification not in SUPPORTED_CLASSIFICATIONS:
        raise AuthoritativeOverrideError(
            f"{location}.jurisdiction.classification must be supported"
        )
    suffix = _require_string(
        jurisdiction["jurisdiction_type_suffix"],
        f"{location}.jurisdiction.jurisdiction_type_suffix",
    )
    if suffix != classification:
        raise AuthoritativeOverrideError(
            f"{location}.jurisdiction_type_suffix must equal classification"
        )
    jurisdiction["jurisdiction_name"] = _require_string(
        jurisdiction["jurisdiction_name"],
        f"{location}.jurisdiction.jurisdiction_name",
    )
    jurisdiction["url"] = _require_string(
        jurisdiction["url"], f"{location}.jurisdiction.url"
    )

    source = _require_mapping(item["source"], f"{location}.source")
    if set(source) != {"source_name", "source_url", "source_description"}:
        raise AuthoritativeOverrideError(
            f"{location}.source must contain source_name, source_url, and source_description"
        )
    source["source_name"] = _require_string(
        source["source_name"], f"{location}.source.source_name"
    )
    source_urls = _require_mapping(source["source_url"], f"{location}.source.source_url")
    if not source_urls:
        raise AuthoritativeOverrideError(f"{location}.source.source_url must not be empty")
    source["source_url"] = {
        _require_string(key, f"{location}.source.source_url key"): _require_string(
            value, f"{location}.source.source_url.{key}"
        )
        for key, value in source_urls.items()
    }
    source["source_description"] = _require_string(
        source["source_description"], f"{location}.source.source_description"
    )

    return AuthoritativeOverride(
        override_id=_require_string(item["override_id"], f"{location}.override_id"),
        state=state,
        canonical_name=canonical_name,
        aliases=aliases,
        ocdid=ocdid,
        validation_geoid=validation_geoid,
        jurisdiction=jurisdiction,
        source=source,
        verified_asof=_require_string(
            item["verified_asof"], f"{location}.verified_asof"
        ),
        evidence_notes=_require_string(
            item["evidence_notes"], f"{location}.evidence_notes"
        ),
    )


def load_authoritative_overrides(
    path: str | Path,
) -> tuple[AuthoritativeOverride, ...]:
    registry_path = Path(path)
    try:
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuthoritativeOverrideError(f"override registry not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise AuthoritativeOverrideError(f"override registry is invalid YAML: {path}") from exc

    root = _require_mapping(raw, "registry")
    if set(root) != {"version", "overrides"} or root["version"] != 1:
        raise AuthoritativeOverrideError(
            "override registry must contain version: 1 and overrides"
        )
    raw_overrides = root["overrides"]
    if not isinstance(raw_overrides, list) or not raw_overrides:
        raise AuthoritativeOverrideError("override registry must contain overrides")

    overrides = tuple(
        _parse_override(item, index) for index, item in enumerate(raw_overrides)
    )
    seen_ids: set[str] = set()
    seen_aliases: set[tuple[str, str]] = set()
    for override in overrides:
        if override.override_id in seen_ids:
            raise AuthoritativeOverrideError(
                f"duplicate override_id: {override.override_id}"
            )
        seen_ids.add(override.override_id)
        for alias in override.aliases:
            key = (override.state, normalize_override_name(alias))
            if key in seen_aliases:
                raise AuthoritativeOverrideError(
                    f"duplicate state/name override alias: {key}"
                )
            seen_aliases.add(key)
    return overrides


def resolve_authoritative_override(
    overrides: tuple[AuthoritativeOverride, ...], *, state: str, name: str
) -> AuthoritativeOverride | None:
    key = (state.lower(), normalize_override_name(name))
    for override in overrides:
        aliases = {
            (override.state, normalize_override_name(alias))
            for alias in override.aliases
        }
        if key in aliases:
            return override
    return None


def authoritative_override_to_dict(
    override: AuthoritativeOverride,
) -> Mapping[str, Any]:
    result = {
        "override_id": override.override_id,
        "state": override.state,
        "canonical_name": override.canonical_name,
        "aliases": list(override.aliases),
        "ocdid": override.ocdid,
        "jurisdiction": dict(override.jurisdiction),
        "source": dict(override.source),
        "verified_asof": override.verified_asof,
        "evidence_notes": override.evidence_notes,
    }
    if override.validation_geoid is not None:
        result["validation_geoid"] = override.validation_geoid
    return result
