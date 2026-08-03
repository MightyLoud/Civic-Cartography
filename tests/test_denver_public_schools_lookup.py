from __future__ import annotations

from pathlib import Path

import yaml

from scripts.capture_upstream_fixtures import Candidate, _resolve_target


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "batch_pilot_25.yml"
DENVER_DPS_OCDID = (
    "ocd-division/country:us/state:co/county:denver/"
    "school_district:school_district_no._1"
)


def _denver_target() -> dict:
    raw = yaml.safe_load(PILOT_MANIFEST.read_text(encoding="utf-8"))
    return next(
        target for target in raw["targets"] if target["target_id"] == "BP25-015"
    )


def test_denver_public_schools_uses_upstream_exact_lookup_name() -> None:
    target = _denver_target()

    assert target["jurisdiction_name"] == "Denver Public Schools"
    assert target["selector"] == {
        "type": "explicit_lookup",
        "name": "School District No. 1",
        "resolution_policy": "override_or_exception",
    }
    assert target["expected_classification"] == "school_system"


def test_denver_public_schools_resolves_unique_master_candidate() -> None:
    target = _denver_target()
    candidate = Candidate(
        ocdid=DENVER_DPS_OCDID,
        name="school district no. 1",
        source="master_orphan",
        ingest=object(),
    )

    selected, status, reason = _resolve_target(
        target,
        {DENVER_DPS_OCDID: candidate},
    )

    assert selected == [candidate]
    assert status == "matched"
    assert reason is None
