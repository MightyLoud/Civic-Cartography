from __future__ import annotations

from pathlib import Path

import yaml

from scripts.capture_upstream_fixtures import Candidate, _resolve_target


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "batch_pilot_25.yml"
SEATTLE_SPS_OCDID = (
    "ocd-division/country:us/state:wa/county:king/"
    "school_district:seattle_public_schools"
)


def _seattle_target() -> dict:
    raw = yaml.safe_load(PILOT_MANIFEST.read_text(encoding="utf-8"))
    return next(
        target for target in raw["targets"] if target["target_id"] == "BP25-016"
    )


def test_seattle_public_schools_uses_upstream_exact_lookup_name() -> None:
    target = _seattle_target()

    assert target["jurisdiction_name"] == "Seattle Public Schools"
    assert target["selector"] == {
        "type": "explicit_lookup",
        "name": "Seattle Public Schools",
        "resolution_policy": "override_or_exception",
    }
    assert target["expected_classification"] == "school_system"


def test_seattle_public_schools_resolves_unique_master_candidate() -> None:
    target = _seattle_target()
    candidate = Candidate(
        ocdid=SEATTLE_SPS_OCDID,
        name="seattle public schools",
        source="master_orphan",
        ingest=object(),
    )

    selected, status, reason = _resolve_target(
        target,
        {SEATTLE_SPS_OCDID: candidate},
    )

    assert selected == [candidate]
    assert status == "matched"
    assert reason is None
