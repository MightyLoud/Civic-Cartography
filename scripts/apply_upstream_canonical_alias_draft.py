from __future__ import annotations

import argparse
from pathlib import Path


class DraftPatchError(ValueError):
    """Raised when the pinned upstream source no longer matches the draft."""


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise DraftPatchError(f"{label}: expected one source block, found {count}")
    return text.replace(old, new, 1)


def _update_request_model(upstream_root: Path) -> None:
    path = upstream_root / "src" / "init_migration" / "pipeline_models.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        """    jurisdiction_override: dict[str, Any] | None = None
    source_override: dict[str, Any] | None = None
    asof_datetime: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
""",
        """    jurisdiction_override: dict[str, Any] | None = None
    source_override: dict[str, Any] | None = None
    canonical_jurisdiction_id: str | None = None
    suppress_jurisdiction_generation: bool = False
    asof_datetime: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
""",
        "GeneratorReq canonical alias fields",
    )
    path.write_text(text, encoding="utf-8")


def _update_generation_pipeline(upstream_root: Path) -> None:
    path = upstream_root / "src" / "init_migration" / "generate_pipeline.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        """        jurisdiction_ocdid = self._derive_jurisdiction_ocdid(
            self.division.ocdid, classification
        )
        self.division.jurisdiction_id = jurisdiction_ocdid
        if getattr(self.req, "data", None) is not None:
            div_gen = DivGenerator(self.req)
            div_gen.division = self.division
            response.division_path = str(
                div_gen.dump_division(output_dir=self.division_output_dir)
            )

        if self.jurisdiction_exists(jurisdiction_ocdid):
""",
        """        canonical_jurisdiction_id = getattr(
            self.req, "canonical_jurisdiction_id", None
        ) or (
            raw_record.get("_canonical_jurisdiction_ocdid")
            if isinstance(raw_record, dict)
            else None
        )
        suppress_jurisdiction_generation = bool(
            getattr(self.req, "suppress_jurisdiction_generation", False)
            or (
                raw_record.get("_suppress_jurisdiction_generation", False)
                if isinstance(raw_record, dict)
                else False
            )
        )
        jurisdiction_ocdid = canonical_jurisdiction_id or self._derive_jurisdiction_ocdid(
            self.division.ocdid, classification
        )
        self.division.jurisdiction_id = jurisdiction_ocdid
        if getattr(self.req, "data", None) is not None:
            div_gen = DivGenerator(self.req)
            div_gen.division = self.division
            response.division_path = str(
                div_gen.dump_division(output_dir=self.division_output_dir)
            )

        if suppress_jurisdiction_generation:
            logger.info(
                "Canonical alias member references shared Jurisdiction without duplicate generation",
                extra={
                    "division_ocdid": self.division.ocdid,
                    "canonical_jurisdiction_ocdid": jurisdiction_ocdid,
                },
            )
            return

        if self.jurisdiction_exists(jurisdiction_ocdid):
""",
        "canonical alias generation branch",
    )
    path.write_text(text, encoding="utf-8")


def _write_tests(upstream_root: Path) -> None:
    path = (
        upstream_root
        / "tests"
        / "src"
        / "init_migration"
        / "test_canonical_alias_generation.py"
    )
    path.write_text(
        '''from types import SimpleNamespace
from uuid import UUID

import src.init_migration.generate_pipeline as generate_pipeline
from src.init_migration.generate_pipeline import GeneratePipeline


PLACE = "ocd-division/country:us/state:co/place:denver"
COUNTY = "ocd-division/country:us/state:co/county:denver"
JURISDICTION = "ocd-jurisdiction/country:us/state:co/place:denver/government"
TEST_UUID = UUID("9e7f9899-e6e9-5a53-a12f-723bb5542fed")


def _pipeline(raw_record, division, tmp_path):
    pipeline = GeneratePipeline.__new__(GeneratePipeline)
    pipeline.req = SimpleNamespace(
        data=SimpleNamespace(),
        jurisdiction_override=None,
        canonical_jurisdiction_id=None,
        suppress_jurisdiction_generation=False,
    )
    pipeline.data = SimpleNamespace(raw_record=raw_record)
    pipeline.uuid = TEST_UUID
    pipeline.division = division
    pipeline.jurisdiction = None
    pipeline.created_jurisdictions = set()
    pipeline.division_output_dir = tmp_path
    pipeline.jurisdiction_output_dir = tmp_path
    return pipeline


def _seed(**kwargs):
    return SimpleNamespace(
        has_jurisdiction=True,
        classification="government",
        reason="general government fallback",
    )


def test_secondary_alias_member_references_canonical_without_duplicate(
    monkeypatch,
    tmp_path,
):
    raw_record = {
        "_canonical_jurisdiction_ocdid": JURISDICTION,
        "_suppress_jurisdiction_generation": True,
    }
    division = SimpleNamespace(ocdid=COUNTY, jurisdiction_id=None)
    pipeline = _pipeline(raw_record, division, tmp_path)
    response = SimpleNamespace(division_path=None, jurisdiction_path=None)
    division_path = tmp_path / "divisions/co/local/denver_county.yaml"

    class FakeDivGenerator:
        def __init__(self, req):
            assert req is pipeline.req
            self.division = None

        def dump_division(self, output_dir):
            assert self.division is division
            assert output_dir == tmp_path
            return division_path

    class DuplicateJurisdictionGenerator:
        def __init__(self, *args, **kwargs):
            raise AssertionError("secondary alias member generated a duplicate Jurisdiction")

    monkeypatch.setattr(generate_pipeline, "infer_jurisdiction_seed", _seed)
    monkeypatch.setattr(generate_pipeline, "DivGenerator", FakeDivGenerator)
    monkeypatch.setattr(
        generate_pipeline,
        "JurGenerator",
        DuplicateJurisdictionGenerator,
    )

    pipeline._generate_jurisdiction_for_division(response, lsad_code=None)

    assert division.jurisdiction_id == JURISDICTION
    assert response.division_path == str(division_path)
    assert response.jurisdiction_path is None
    assert pipeline.created_jurisdictions == set()


def test_canonical_alias_member_generates_shared_jurisdiction(
    monkeypatch,
    tmp_path,
):
    raw_record = {
        "_canonical_jurisdiction_ocdid": JURISDICTION,
        "_suppress_jurisdiction_generation": False,
    }
    division = SimpleNamespace(ocdid=PLACE, jurisdiction_id=None)
    pipeline = _pipeline(raw_record, division, tmp_path)
    response = SimpleNamespace(division_path=None, jurisdiction_path=None)
    division_path = tmp_path / "divisions/co/local/denver_place.yaml"
    jurisdiction_path = tmp_path / "jurisdictions/co/local/denver.yaml"

    class FakeDivGenerator:
        def __init__(self, req):
            assert req is pipeline.req
            self.division = None

        def dump_division(self, output_dir):
            assert self.division is division
            assert output_dir == tmp_path
            return division_path

    class FakeJurGenerator:
        def __init__(self, req, division):
            assert req is pipeline.req
            assert division is pipeline.division

        def generate_jurisdiction(self, *, division, uuid, classification):
            assert division is pipeline.division
            assert uuid == TEST_UUID
            assert classification == "government"
            return SimpleNamespace()

        def dump_jurisdiction(self, output_dir):
            assert output_dir == tmp_path
            return jurisdiction_path

    monkeypatch.setattr(generate_pipeline, "infer_jurisdiction_seed", _seed)
    monkeypatch.setattr(generate_pipeline, "DivGenerator", FakeDivGenerator)
    monkeypatch.setattr(generate_pipeline, "JurGenerator", FakeJurGenerator)

    pipeline._generate_jurisdiction_for_division(response, lsad_code=None)

    assert division.jurisdiction_id == JURISDICTION
    assert response.division_path == str(division_path)
    assert response.jurisdiction_path == str(jurisdiction_path)
    assert pipeline.created_jurisdictions == {JURISDICTION}
''',
        encoding="utf-8",
    )


def apply_draft(upstream_root: Path) -> None:
    _update_request_model(upstream_root)
    _update_generation_pipeline(upstream_root)
    _write_tests(upstream_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", required=True)
    args = parser.parse_args()
    apply_draft(Path(args.upstream_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
