from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "batch_pilot_25.yml"


def test_miami_dade_uses_canonical_hyphenated_ocdid() -> None:
    raw = yaml.safe_load(PILOT_MANIFEST.read_text(encoding="utf-8"))
    targets = {target["target_id"]: target for target in raw["targets"]}

    selector = targets["BP25-012"]["selector"]

    assert selector == {
        "type": "ocdid",
        "value": "ocd-division/country:us/state:fl/county:miami-dade",
    }
    assert "miami_dade" not in selector["value"]
