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


def apply_draft(upstream_root: Path) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", required=True)
    args = parser.parse_args()
    apply_draft(Path(args.upstream_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
