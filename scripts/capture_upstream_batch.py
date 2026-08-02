from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

import capture_upstream_fixtures as base_capture


class BatchCaptureError(ValueError):
    """Raised when a full target-manifest capture cannot be completed safely."""


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


def _ensure_sources_for_states(
    api: dict[str, Any], source_dir: Path, states: list[str]
) -> dict[str, Any]:
    files: dict[str, Path] = {
        "master": source_dir / "country-us.csv",
        "validation": source_dir / "nested-divisions-validation.csv",
    }
    urls: dict[str, str] = {
        "master": api["master_url"],
        "validation": api["validation_url"],
    }
    for state in states:
        key = f"{state}_local"
        files[key] = source_dir / f"state-{state}-local_gov.csv"
        urls[key] = api["local_url"](state)

    for key, path in files.items():
        base_capture._download_once(urls[key], path)

    manifest = {
        "version": 1,
        "states": states,
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
    states = sorted({str(target["state"]) for target in targets})
    api = base_capture._configure_upstream(upstream_root, fixed_asof)
    sources = _ensure_sources_for_states(api, source_dir, states)

    work_dir.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "data" / "ocdid_pipeline.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    csv_backup = work_dir / "data" / "ocdid_uuid_lookup.csv"

    manager = api["DownloadManager"](states=states, db_path=str(db_path))
    manager.load_master_csv(sources["files"]["master"].read_bytes())
    for state in states:
        raw_local = sources["files"][f"{state}_local"].read_bytes()
        manager.load_local_csv(_normalize_local_csv(raw_local), state)

    matcher = api["OCDidMatcher"](
        db_path=str(db_path),
        states=states,
        csv_backup_path=str(csv_backup),
    )
    match_results = matcher.run_matching(show_progress=False)
    candidates = base_capture._candidate_index(api, match_results)

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
            sources["files"]["validation"],
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
                "matcher": {
                    "states": states,
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
