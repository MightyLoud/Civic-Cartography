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


def _apply_pipeline_compat(upstream_root: Path) -> None:
    path = upstream_root / "src" / "init_migration" / "generate_pipeline.py"
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        """        exact_override = getattr(self.req, \"jurisdiction_override\", None) or (
            self.data.raw_record.get(\"_jurisdiction_override\")
            if isinstance(self.data.raw_record, dict)
            else None
        )
""",
        """        data = getattr(self, \"data\", None)
        raw_record = getattr(data, \"raw_record\", {})
        exact_override = getattr(self.req, \"jurisdiction_override\", None) or (
            raw_record.get(\"_jurisdiction_override\")
            if isinstance(raw_record, dict)
            else None
        )
""",
        "pipeline override compatibility",
    )
    text = _replace_once(
        text,
        """        self.division.jurisdiction_id = jurisdiction_ocdid
        div_gen = DivGenerator(self.req)
        div_gen.division = self.division
        response.division_path = str(
            div_gen.dump_division(output_dir=self.division_output_dir)
        )
""",
        """        self.division.jurisdiction_id = jurisdiction_ocdid
        if getattr(self.req, \"data\", None) is not None:
            div_gen = DivGenerator(self.req)
            div_gen.division = self.division
            response.division_path = str(
                div_gen.dump_division(output_dir=self.division_output_dir)
            )
""",
        "guard Division persistence",
    )
    path.write_text(text, encoding="utf-8")


def _apply_jurisdiction_output(upstream_root: Path) -> None:
    path = upstream_root / "src" / "init_migration" / "generate_jurisdiction.py"
    text = path.read_text(encoding="utf-8")

    text = _replace_once(
        text,
        """            ai = self._ai_lookup(division)

            if classification == \"government\":
""",
        """            ai = self._ai_lookup(division)
            jurisdiction_override = getattr(
                self.req, \"jurisdiction_override\", None
            ) or (
                self.data.raw_record.get(\"_jurisdiction_override\")
                if isinstance(self.data.raw_record, dict)
                else None
            ) or {}
            source_override = getattr(self.req, \"source_override\", None) or (
                self.data.raw_record.get(\"_source_override\")
                if isinstance(self.data.raw_record, dict)
                else None
            ) or {}

            if classification == \"government\":
""",
        "override inputs",
    )
    text = _replace_once(
        text,
        """            name = (ai or {}).get(\"name\") or fallback_name
            url = (ai or {}).get(\"url\") or fallback_url
""",
        """            name = (
                jurisdiction_override.get(\"jurisdiction_name\")
                or (ai or {}).get(\"name\")
                or fallback_name
            )
            url = (
                jurisdiction_override.get(\"url\")
                or (ai or {}).get(\"url\")
                or fallback_url
            )
""",
        "override name and URL",
    )
    text = _replace_once(
        text,
        """                        \"source_name\": \"derived_from_division\",
                        \"source_url\": {
                            \"division\": f\"https://opencivicdata.org/division/{division.ocdid}\"
                        },
                        \"source_type\": SourceType.HUMAN,
                        \"source_description\": \"Jurisdiction derived from Division object\",
""",
        """                        \"source_name\": source_override.get(
                            \"source_name\", \"derived_from_division\"
                        ),
                        \"source_url\": source_override.get(\"source_url\")
                        or {
                            \"division\": f\"https://opencivicdata.org/division/{division.ocdid}\"
                        },
                        \"source_type\": SourceType.HUMAN,
                        \"source_description\": source_override.get(
                            \"source_description\",
                            \"Jurisdiction derived from Division object\",
                        ),
""",
        "override provenance",
    )

    path.write_text(text, encoding="utf-8")


def _apply_override_test_compat(upstream_root: Path) -> None:
    path = (
        upstream_root
        / "tests"
        / "src"
        / "init_migration"
        / "test_authoritative_jurisdiction_override.py"
    )
    text = path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        """    pipeline.req = SimpleNamespace(jurisdiction_override=None)
""",
        """    pipeline.req = SimpleNamespace(
        jurisdiction_override=None,
        data=SimpleNamespace(),
    )
""",
        "authoritative override test request data",
    )
    path.write_text(text, encoding="utf-8")


def apply_draft(upstream_root: Path) -> None:
    _apply_pipeline_compat(upstream_root)
    _apply_jurisdiction_output(upstream_root)
    _apply_override_test_compat(upstream_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", required=True)
    args = parser.parse_args()
    apply_draft(Path(args.upstream_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
