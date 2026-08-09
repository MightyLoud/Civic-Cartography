from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import yaml

import capture_upstream_fixtures as base_capture


class BatchCaptureError(ValueError):
    """Raised when a full target-manifest capture cannot be completed safely."""


US_ADMIN1_TYPES = ("state", "district", "territory")
TERRITORY_COUNTY_SEGMENTS = ("county", "municipio")
TERRITORY_COUNTIES_GID = "691893868"


def _load_manifest_targets(path: Path) -> list[dict[str, Any]]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BatchCaptureError(f"target manifest not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise BatchCaptureError(f"target manifest is invalid YAML: {path}") from exc

    targets = raw.get("targets") if isinstance(raw, dict) else None
    if not isinstance(targets, list) or not targets:
        raise BatchCaptureError("target manifest must contain a non-empty targets list")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_target in enumerate(targets):
        if not isinstance(raw_target, dict):
            raise BatchCaptureError(f"target[{index}] must be a mapping")
        target = dict(raw_target)
        target_id = target.get("target_id")
        state = target.get("state")
        if not isinstance(target_id, str) or not target_id:
            raise BatchCaptureError(f"target[{index}].target_id must be a string")
        if target_id in seen_ids:
            raise BatchCaptureError(f"duplicate target_id: {target_id}")
        seen_ids.add(target_id)
        if not isinstance(state, str) or len(state.strip()) != 2:
            raise BatchCaptureError(f"target[{index}].state must be a two-letter code")
        target["state"] = state.strip().lower()
        normalized.append(target)
    return normalized


def _normalize_local_csv(csv_bytes: bytes) -> bytes:
    """Project variable-width local CSV rows onto the upstream id/name contract."""
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BatchCaptureError("state-local CSV must be UTF-8") from exc

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for row_number, row in enumerate(csv.reader(io.StringIO(text)), start=1):
        if not row or not any(value.strip() for value in row):
            continue
        if len(row) < 2:
            raise BatchCaptureError(
                f"state-local CSV row {row_number} has fewer than two columns"
            )

        ocdid = row[0].strip()
        name = row[1].strip()
        if ocdid.lower() in {"id", "ocdid"} and name.lower() == "name":
            continue
        if not ocdid.startswith(("ocd-division/", "ocd-jurisdiction/")):
            raise BatchCaptureError(
                f"state-local CSV row {row_number} has invalid OCD ID {ocdid!r}"
            )
        writer.writerow([ocdid, name])
    return output.getvalue().encode("utf-8")


def _selector_ocdids(target: dict[str, Any]) -> list[str]:
    selector = target.get("selector")
    if not isinstance(selector, dict):
        return []
    if selector.get("type") == "ocdid":
        value = selector.get("value")
        return [value] if isinstance(value, str) and value else []
    if selector.get("type") == "alias_group":
        members = selector.get("members")
        if isinstance(members, list):
            return [member for member in members if isinstance(member, str) and member]
    return []


def _target_admin1_type(target: dict[str, Any]) -> str:
    """Resolve the OCDID admin-1 segment represented by a manifest target."""
    state = str(target["state"])
    ocdids = _selector_ocdids(target)
    if not ocdids:
        # Maintained explicit-lookups currently resolve state-scoped overrides.
        return "state"

    kinds: set[str] = set()
    for ocdid in ocdids:
        padded = f"/{ocdid.rstrip('/')}/"
        matches = {
            kind
            for kind in US_ADMIN1_TYPES
            if f"/{kind}:{state}/" in padded
        }
        if len(matches) != 1:
            raise BatchCaptureError(
                f"{target['target_id']}: selector OCDID must contain exactly one "
                f"supported admin-1 marker for {state}: {ocdid}"
            )
        kinds.update(matches)
    if len(kinds) != 1:
        raise BatchCaptureError(
            f"{target['target_id']}: selector OCDIDs span multiple admin-1 types: "
            f"{sorted(kinds)}"
        )
    return next(iter(kinds))


def _target_uses_territory_counties_validation(
    target: dict[str, Any], admin1_type: str
) -> bool:
    """Return whether a territory target represents a county-equivalent."""
    if admin1_type != "territory":
        return False
    return any(
        f"/{segment}:" in f"/{ocdid.rstrip('/')}/"
        for ocdid in _selector_ocdids(target)
        for segment in TERRITORY_COUNTY_SEGMENTS
    )


def _validation_url_with_gid(url: str, gid: str) -> str:
    """Retarget one Google Sheets CSV export URL to a stable sheet ID."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["gid"] = gid
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _combine_validation_csvs(paths: list[Path], output_path: Path) -> Path:
    """Combine compatible retained validation exports for one generator run."""
    if not paths:
        raise BatchCaptureError("at least one validation CSV is required")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_header: list[str] | None = None
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        for path in paths:
            try:
                source = path.open("r", encoding="utf-8-sig", newline="")
            except FileNotFoundError as exc:
                raise BatchCaptureError(f"validation CSV not found: {path}") from exc
            with source:
                reader = csv.reader(source)
                header = next(reader, None)
                if not header:
                    raise BatchCaptureError(f"validation CSV has no header: {path}")
                if expected_header is None:
                    expected_header = header
                    writer.writerow(header)
                elif header != expected_header:
                    raise BatchCaptureError(
                        f"validation CSV header does not match retained sources: {path}"
                    )
                for row in reader:
                    if row and any(value.strip() for value in row):
                        writer.writerow(row)
    return output_path


def _master_candidates(
    api: dict[str, Any], master_bytes: bytes, requested_ocdids: set[str]
) -> dict[str, Any]:
    """Build exact candidates for non-state targets from the national master."""
    if not requested_ocdids:
        return {}
    try:
        text = master_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BatchCaptureError("national master CSV must be UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not {"id", "name"}.issubset(reader.fieldnames):
        raise BatchCaptureError("national master CSV must contain id and name columns")

    candidates: dict[str, Any] = {}
    for raw_row in reader:
        row = {str(key): value or "" for key, value in raw_row.items() if key is not None}
        ocdid = row.get("id", "").strip()
        if ocdid not in requested_ocdids:
            continue
        if ocdid in candidates:
            raise BatchCaptureError(f"national master contains duplicate OCDID: {ocdid}")
        name = row.get("name", "").strip()
        if not name:
            raise BatchCaptureError(f"national master target has no name: {ocdid}")
        ingest = base_capture._make_ingest(api, ocdid, name)
        ingest.raw_record.clear()
        ingest.raw_record.update(row)
        candidates[ocdid] = base_capture.Candidate(
            ocdid=ocdid,
            name=name,
            source="master",
            ingest=ingest,
        )

    missing = sorted(requested_ocdids - set(candidates))
    if missing:
        raise BatchCaptureError(
            f"non-state target OCDIDs missing from national master: {missing}"
        )
    return candidates


def _ensure_sources_for_states(
    api: dict[str, Any],
    source_dir: Path,
    states: list[str],
    *,
    districts: list[str] | None = None,
    territories: list[str] | None = None,
    include_territory_counties: bool = False,
) -> dict[str, Any]:
    districts = districts or []
    territories = territories or []
    files: dict[str, Path] = {
        "master": source_dir / "country-us.csv",
        "validation": source_dir / "nested-divisions-validation.csv",
    }
    urls: dict[str, str] = {
        "master": api["master_url"],
        "validation": api["validation_url"],
    }
    if include_territory_counties:
        key = "territory_counties_validation"
        files[key] = source_dir / "nested-divisions-territory-counties-validation.csv"
        urls[key] = _validation_url_with_gid(
            api["validation_url"], TERRITORY_COUNTIES_GID
        )
    for state in states:
        key = f"{state}_local"
        files[key] = source_dir / f"state-{state}-local_gov.csv"
        urls[key] = api["local_url"](state)

    for key, path in files.items():
        base_capture._download_once(urls[key], path)

    manifest = {
        "version": 1,
        "states": states,
        "districts": districts,
        "territories": territories,
        "non_state_strategy": (
            "retain the national master as RAW and resolve exact district/territory "
            "selectors from that master; do not invent nonexistent state-local URLs"
        ),
        "validation_strategy": {
            "municipalities_retained": True,
            "territory_counties_retained": include_territory_counties,
            "strategy": (
                "combine compatible retained validation exports for the generator "
                "when a territory county-equivalent target is present"
            ),
        },
        "local_csv_normalization": {
            "columns": ["id", "name"],
            "strategy": (
                "parse CSV, skip a recognized id/name header, validate OCD IDs, "
                "and retain the first two fields"
            ),
        },
        "files": {
            key: {
                "path": path.name,
                "url": urls[key],
                "sha256": base_capture._sha256_bytes(path.read_bytes()),
                "size_bytes": path.stat().st_size,
            }
            for key, path in sorted(files.items())
        },
    }
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "source-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"files": files, "manifest": manifest}


async def capture_batch(args: argparse.Namespace) -> None:
    upstream_root = Path(args.upstream_root).resolve()
    manifest_path = Path(args.target_manifest).resolve()
    source_dir = Path(args.source_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    artifact_root = work_dir / "artifacts"
    execution_path = Path(args.execution_results).resolve()
    diagnostics_path = Path(args.diagnostics).resolve()
    fixed_asof = base_capture._parse_asof(args.run_asof)

    if not (upstream_root / "src" / "init_migration").is_dir():
        raise BatchCaptureError(f"upstream checkout is invalid: {upstream_root}")

    targets = _load_manifest_targets(manifest_path)
    admin1_types = {
        str(target["target_id"]): _target_admin1_type(target) for target in targets
    }
    states = sorted(
        {
            str(target["state"])
            for target in targets
            if admin1_types[str(target["target_id"])] == "state"
        }
    )
    districts = sorted(
        {
            str(target["state"])
            for target in targets
            if admin1_types[str(target["target_id"])] == "district"
        }
    )
    territories = sorted(
        {
            str(target["state"])
            for target in targets
            if admin1_types[str(target["target_id"])] == "territory"
        }
    )
    include_territory_counties = any(
        _target_uses_territory_counties_validation(
            target, admin1_types[str(target["target_id"])]
        )
        for target in targets
    )
    api = base_capture._configure_upstream(upstream_root, fixed_asof)
    sources = _ensure_sources_for_states(
        api,
        source_dir,
        states,
        districts=districts,
        territories=territories,
        include_territory_counties=include_territory_counties,
    )

    work_dir.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "data" / "ocdid_pipeline.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    csv_backup = work_dir / "data" / "ocdid_uuid_lookup.csv"
    validation_paths = [sources["files"]["validation"]]
    if include_territory_counties:
        validation_paths.append(sources["files"]["territory_counties_validation"])
    effective_validation_path = (
        validation_paths[0]
        if len(validation_paths) == 1
        else _combine_validation_csvs(
            validation_paths,
            work_dir / "data" / "nested-divisions-effective-validation.csv",
        )
    )

    manager = api["DownloadManager"](states=states, db_path=str(db_path))
    manager.load_master_csv(sources["files"]["master"].read_bytes())
    for state in states:
        raw_local = sources["files"][f"{state}_local"].read_bytes()
        manager.load_local_csv(_normalize_local_csv(raw_local), state)

    if states:
        matcher = api["OCDidMatcher"](
            db_path=str(db_path),
            states=states,
            csv_backup_path=str(csv_backup),
        )
        match_results = matcher.run_matching(show_progress=False)
    else:
        match_results = SimpleNamespace(
            matched=[], local_orphans=[], master_orphans=[]
        )
    candidates = base_capture._candidate_index(api, match_results)
    requested_master_ocdids = {
        ocdid
        for target in targets
        if admin1_types[str(target["target_id"])] != "state"
        for ocdid in _selector_ocdids(target)
    }
    for ocdid, candidate in _master_candidates(
        api,
        sources["files"]["master"].read_bytes(),
        requested_master_ocdids,
    ).items():
        candidates.setdefault(ocdid, candidate)

    overlays: dict[str, dict[str, Any]] = {}
    diagnostics: list[dict[str, Any]] = []
    for target in targets:
        selected, match_status, reason = base_capture._resolve_target(target, candidates)
        overlay, detail = await base_capture._capture_target(
            api,
            target,
            selected,
            match_status,
            reason,
            fixed_asof,
            effective_validation_path,
            artifact_root,
        )
        overlays[str(target["target_id"])] = overlay
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
                "validation": {
                    "territory_counties_required": include_territory_counties,
                    "retained_source_keys": [
                        "validation",
                        *(
                            ["territory_counties_validation"]
                            if include_territory_counties
                            else []
                        ),
                    ],
                    "effective_path": effective_validation_path.name,
                },
                "matcher": {
                    "states": states,
                    "districts": districts,
                    "territories": territories,
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
        description=(
            "Capture every target in a target manifest from a pinned upstream "
            "checkout."
        )
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
        asyncio.run(capture_batch(args))
    except (
        BatchCaptureError,
        base_capture.CaptureError,
        httpx.HTTPError,
        OSError,
        ValueError,
    ) as exc:
        print(f"upstream-batch-capture error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
