from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx
import yaml

FIXTURE_IDS = (
    "BP25-001",
    "BP25-002",
    "BP25-009",
    "BP25-014",
    "BP25-018",
    "BP25-022",
)

# Maintained exact-name aliases. These are selectors, not fuzzy matches.
EXPLICIT_NAME_ALIASES: dict[str, set[str]] = {
    "BP25-014": {
        "colorado springs school district 11",
        "colorado springs school district no 11",
        "colorado springs 11 school district",
        "school district no 11 in the county of el paso and state of colorado",
    },
    "BP25-018": {
        "regional transportation district",
        "regional transportation district colorado",
        "denver regional transportation district",
        "regional transportation district rtd",
    },
}


class CaptureError(ValueError):
    """Raised when an upstream capture cannot be completed safely."""


@dataclass(frozen=True)
class Candidate:
    ocdid: str
    name: str
    source: str
    ingest: Any


def _normalize_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _parse_asof(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise CaptureError("run_asof must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise CaptureError("run_asof must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _download_once(url: str, path: Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    path.write_bytes(response.content)


def _configure_upstream(upstream_root: Path, fixed_asof: datetime) -> dict[str, Any]:
    sys.path.insert(0, str(upstream_root))

    from src.init_migration import generate_division, generate_jurisdiction
    from src.init_migration.download_manager import (
        LOCAL_TEMPLATE,
        MASTER_PATH,
        RAW_BASE,
        DownloadManager,
    )
    from src.init_migration.generate_pipeline import GeneratePipeline
    from src.init_migration.jurisdiction_seed import infer_jurisdiction_seed
    from src.init_migration.ocdid_matcher import OCDidMatcher
    from src.init_migration.pipeline_models import (
        DIVISIONS_SHEET_CSV_URL,
        GeneratorReq,
        OCDidIngestResp,
    )
    from src.models.ocdid import OCDIdParsed
    from src.utils.ocdid import ocdid_parser

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            if tz is None:
                return fixed_asof.replace(tzinfo=None)
            return fixed_asof.astimezone(tz)

    # Upstream currently calls datetime.now() independently for Division and
    # Jurisdiction last_updated fields. Patch only the imported module clocks so
    # both clean captures receive the same explicit timestamp.
    generate_division.datetime = FixedDateTime
    generate_jurisdiction.datetime = FixedDateTime

    return {
        "DownloadManager": DownloadManager,
        "OCDidMatcher": OCDidMatcher,
        "GeneratePipeline": GeneratePipeline,
        "GeneratorReq": GeneratorReq,
        "OCDidIngestResp": OCDidIngestResp,
        "OCDIdParsed": OCDIdParsed,
        "ocdid_parser": ocdid_parser,
        "infer_jurisdiction_seed": infer_jurisdiction_seed,
        "master_url": f"{RAW_BASE}/{MASTER_PATH}",
        "local_url": lambda state: f"{RAW_BASE}/{LOCAL_TEMPLATE.format(state=state)}",
        "validation_url": DIVISIONS_SHEET_CSV_URL,
    }


def _ensure_sources(api: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    files = {
        "master": source_dir / "country-us.csv",
        "wa_local": source_dir / "state-wa-local_gov.csv",
        "co_local": source_dir / "state-co-local_gov.csv",
        "validation": source_dir / "nested-divisions-validation.csv",
    }
    urls = {
        "master": api["master_url"],
        "wa_local": api["local_url"]("wa"),
        "co_local": api["local_url"]("co"),
        "validation": api["validation_url"],
    }
    for key, path in files.items():
        _download_once(urls[key], path)

    manifest = {
        "version": 1,
        "files": {
            key: {
                "path": path.name,
                "url": urls[key],
                "sha256": _sha256_bytes(path.read_bytes()),
                "size_bytes": path.stat().st_size,
            }
            for key, path in sorted(files.items())
        },
    }
    (source_dir / "source-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"files": files, "manifest": manifest}


def _load_manifest_fixtures(path: Path) -> list[dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    targets = raw.get("targets") if isinstance(raw, dict) else None
    if not isinstance(targets, list):
        raise CaptureError("target manifest must contain a targets list")
    by_id = {
        target.get("target_id"): target
        for target in targets
        if isinstance(target, dict) and target.get("target_id") in FIXTURE_IDS
    }
    missing = [target_id for target_id in FIXTURE_IDS if target_id not in by_id]
    if missing:
        raise CaptureError(f"manifest is missing regression fixtures: {missing}")
    return [by_id[target_id] for target_id in FIXTURE_IDS]


def _make_ingest(api: dict[str, Any], ocdid: str, name: str) -> Any:
    parsed_dict = api["ocdid_parser"](ocdid)
    parsed = api["OCDIdParsed"](
        base_ocdid=ocdid,
        raw_ocdid=ocdid,
        country=parsed_dict.get("country", "us"),
        state=parsed_dict.get("state"),
        county=parsed_dict.get("county"),
        place=parsed_dict.get("place"),
    )
    return api["OCDidIngestResp"](
        uuid=uuid5(NAMESPACE_URL, ocdid),
        ocdid=parsed,
        raw_record={"id": ocdid, "name": name},
    )


def _candidate_index(api: dict[str, Any], match_results: Any) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    priority = {"matched": 3, "master_orphan": 2, "local_orphan": 1}

    def add(ocdid: str, name: str, source: str, ingest: Any) -> None:
        current = candidates.get(ocdid)
        if current is None or priority[source] > priority[current.source]:
            candidates[ocdid] = Candidate(ocdid, name, source, ingest)

    for ingest in match_results.matched:
        add(
            ingest.ocdid.raw_ocdid,
            str(ingest.raw_record.get("name", "")),
            "matched",
            ingest,
        )
    for row in match_results.master_orphans:
        ocdid = str(row.get("id", ""))
        name = str(row.get("name", ""))
        if ocdid:
            add(ocdid, name, "master_orphan", _make_ingest(api, ocdid, name))
    for row in match_results.local_orphans:
        ocdid = str(row.get("id", ""))
        name = str(row.get("name", ""))
        if ocdid:
            add(ocdid, name, "local_orphan", _make_ingest(api, ocdid, name))
    return candidates


def _resolve_target(
    target: dict[str, Any], candidates: dict[str, Candidate]
) -> tuple[list[Candidate], str, str | None]:
    target_id = target["target_id"]
    selector = target["selector"]
    selector_type = selector["type"]

    if selector_type == "ocdid":
        candidate = candidates.get(selector["value"])
        if candidate is None:
            return (
                [],
                "not_found",
                "Exact OCD ID was not present in matched or orphan upstream records.",
            )
        return [candidate], "matched", None

    if selector_type == "alias_group":
        resolved = [
            candidates[value] for value in selector["members"] if value in candidates
        ]
        if len(resolved) != len(selector["members"]):
            missing = sorted(
                set(selector["members"]) - {item.ocdid for item in resolved}
            )
            return (
                resolved,
                "alias_group_pending",
                f"Alias members missing from upstream records: {missing}",
            )
        return resolved, "matched", None

    aliases = {
        _normalize_name(selector["name"]),
        *EXPLICIT_NAME_ALIASES.get(target_id, set()),
    }
    matches = [
        candidate
        for candidate in candidates.values()
        if _normalize_name(candidate.name) in aliases
    ]
    matches.sort(key=lambda item: item.ocdid)
    if not matches:
        return (
            [],
            "not_found",
            "No upstream record matched the maintained exact-name aliases: "
            + ", ".join(sorted(aliases)),
        )
    if len(matches) > 1:
        return (
            matches,
            "ambiguous",
            "Multiple upstream records matched the maintained exact-name aliases: "
            + ", ".join(item.ocdid for item in matches),
        )
    return matches, "matched", None


def _relative_artifact(path_value: str | None, artifact_root: Path) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path.relative_to(artifact_root.resolve()).as_posix()


def _read_classification(path: Path) -> str | None:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if isinstance(raw, dict) and isinstance(raw.get("classification"), str):
        return raw["classification"]
    return None


async def _capture_target(
    api: dict[str, Any],
    target: dict[str, Any],
    selected: list[Candidate],
    match_status: str,
    resolution_reason: str | None,
    fixed_asof: datetime,
    validation_path: Path,
    artifact_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target_id = target["target_id"]
    expected = target["expected_classification"]
    attempts: list[dict[str, Any]] = []
    division_paths: list[str] = []
    jurisdiction_paths: list[str] = []
    classifications: list[str] = []

    for candidate in selected:
        req = api["GeneratorReq"](
            data=candidate.ingest,
            validation_data_filepath=str(validation_path),
            asof_datetime=fixed_asof,
        )
        pipeline = api["GeneratePipeline"](
            req,
            division_output_dir=artifact_root,
            jurisdiction_output_dir=artifact_root,
        )
        response = await pipeline.run()
        division_path = _relative_artifact(response.division_path, artifact_root)
        jurisdiction_path = _relative_artifact(response.jurisdiction_path, artifact_root)
        if division_path:
            division_paths.append(division_path)
        if jurisdiction_path:
            jurisdiction_paths.append(jurisdiction_path)
            classification = _read_classification(artifact_root / jurisdiction_path)
            if classification:
                classifications.append(classification)

        seed_reason = None
        if not jurisdiction_path:
            lsad = None
            if division_path:
                try:
                    division_data = yaml.safe_load(
                        (artifact_root / division_path).read_text(encoding="utf-8")
                    )
                    lsad = (
                        division_data.get("government_identifiers", {}).get("lsad")
                        if isinstance(division_data, dict)
                        else None
                    )
                except (OSError, yaml.YAMLError):
                    lsad = None
            try:
                seed = api["infer_jurisdiction_seed"](
                    candidate.ocdid, lsad_code=lsad
                )
                seed_reason = seed.reason
            except Exception as exc:
                seed_reason = f"classifier error: {exc}"

        attempts.append(
            {
                "ocdid": candidate.ocdid,
                "name": candidate.name,
                "source": candidate.source,
                "status": response.status.status.value,
                "error": response.status.error,
                "division_path": division_path,
                "jurisdiction_path": jurisdiction_path,
                "seed_reason": seed_reason,
            }
        )

    division_paths = sorted(set(division_paths))
    jurisdiction_paths = sorted(set(jurisdiction_paths))
    unique_classifications = sorted(set(classifications))
    inferred = unique_classifications[0] if len(unique_classifications) == 1 else None
    classification_status = (
        "matched"
        if inferred == expected
        else "mismatch"
        if inferred is not None
        else "not_evaluated"
    )

    all_complete = bool(selected) and all(
        attempt["status"] == "success"
        and attempt["division_path"]
        and attempt["jurisdiction_path"]
        for attempt in attempts
    )
    if match_status != "matched":
        generation_status = "skipped" if not selected else "partial"
    elif all_complete:
        generation_status = "generated"
    elif division_paths or jurisdiction_paths:
        generation_status = "partial"
    else:
        generation_status = "failed"

    exception_class: str | None = None
    review_reason: str | None = None
    if match_status == "not_found":
        exception_class = "upstream_target_not_found"
        review_reason = resolution_reason
    elif match_status == "ambiguous":
        exception_class = "upstream_target_ambiguous"
        review_reason = resolution_reason
    elif match_status == "alias_group_pending":
        exception_class = "upstream_alias_incomplete"
        review_reason = resolution_reason
    elif generation_status != "generated":
        exception_class = (
            "upstream_partial_generation"
            if (division_paths or jurisdiction_paths)
            else "upstream_generation_failed"
        )
        details = []
        for attempt in attempts:
            parts = [attempt["ocdid"], f"status={attempt['status']}"]
            if attempt["error"]:
                parts.append(f"error={attempt['error']}")
            if attempt["seed_reason"]:
                parts.append(f"seed={attempt['seed_reason']}")
            if not attempt["jurisdiction_path"]:
                parts.append("jurisdiction_path=missing")
            details.append("; ".join(parts))
        review_reason = " | ".join(details) or resolution_reason
    elif classification_status != "matched":
        exception_class = "upstream_classification_mismatch"
        review_reason = f"Expected {expected}; inferred {inferred or 'none'}."

    overlay = {
        "resolved_ocdids": sorted(candidate.ocdid for candidate in selected),
        "match_status": match_status,
        "inferred_classification": inferred,
        "classification_status": classification_status,
        "generation_status": generation_status,
        "division_paths": division_paths,
        "jurisdiction_paths": jurisdiction_paths,
        "exception_class": exception_class,
        "review_reason": review_reason,
        "human_minutes": 0.0,
    }
    diagnostics = {
        "target_id": target_id,
        "jurisdiction_name": target["jurisdiction_name"],
        "match_status": match_status,
        "resolution_reason": resolution_reason,
        "attempts": attempts,
        "overlay": overlay,
    }
    return overlay, diagnostics


async def capture(args: argparse.Namespace) -> None:
    upstream_root = Path(args.upstream_root).resolve()
    manifest_path = Path(args.target_manifest).resolve()
    source_dir = Path(args.source_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    artifact_root = work_dir / "artifacts"
    execution_path = Path(args.execution_results).resolve()
    diagnostics_path = Path(args.diagnostics).resolve()
    fixed_asof = _parse_asof(args.run_asof)

    if not (upstream_root / "src" / "init_migration").is_dir():
        raise CaptureError(f"upstream checkout is invalid: {upstream_root}")

    api = _configure_upstream(upstream_root, fixed_asof)
    sources = _ensure_sources(api, source_dir)
    fixtures = _load_manifest_fixtures(manifest_path)

    work_dir.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "data" / "ocdid_pipeline.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    csv_backup = work_dir / "data" / "ocdid_uuid_lookup.csv"

    manager = api["DownloadManager"](states=["wa", "co"], db_path=str(db_path))
    manager.load_master_csv(sources["files"]["master"].read_bytes())
    manager.load_local_csv(sources["files"]["wa_local"].read_bytes(), "wa")
    manager.load_local_csv(sources["files"]["co_local"].read_bytes(), "co")

    matcher = api["OCDidMatcher"](
        db_path=str(db_path),
        states=["wa", "co"],
        csv_backup_path=str(csv_backup),
    )
    match_results = matcher.run_matching(show_progress=False)
    candidates = _candidate_index(api, match_results)

    overlays: dict[str, dict[str, Any]] = {}
    diagnostics: list[dict[str, Any]] = []
    for target in fixtures:
        selected, match_status, reason = _resolve_target(target, candidates)
        overlay, detail = await _capture_target(
            api,
            target,
            selected,
            match_status,
            reason,
            fixed_asof,
            sources["files"]["validation"],
            artifact_root,
        )
        overlays[target["target_id"]] = overlay
        diagnostics.append(detail)

    execution_path.parent.mkdir(parents=True, exist_ok=True)
    execution_path.write_text(
        json.dumps({"version": 1, "results": overlays}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_path.write_text(
        json.dumps(
            {
                "version": 1,
                "run_asof": fixed_asof.isoformat().replace("+00:00", "Z"),
                "source_manifest": sources["manifest"],
                "matcher": {
                    "matched_count": len(match_results.matched),
                    "local_orphan_count": len(match_results.local_orphans),
                    "master_orphan_count": len(match_results.master_orphans),
                    "candidate_count": len(candidates),
                },
                "targets": diagnostics,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture six regression fixtures from a pinned upstream checkout."
    )
    parser.add_argument("--upstream-root", required=True)
    parser.add_argument("--target-manifest", required=True)
    parser.add_argument("--run-asof", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--execution-results", required=True)
    parser.add_argument("--diagnostics", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        asyncio.run(capture(args))
    except (CaptureError, httpx.HTTPError, OSError, ValueError) as exc:
        print(f"upstream-capture error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
