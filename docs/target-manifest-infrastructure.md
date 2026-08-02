# Target Manifest Batch Mode

Issue: [#43](https://github.com/MightyLoud/Civic-Cartography/issues/43)

## Design decision

Civic-Cartography owns the deliberate acceptance set, manifest validation, deterministic run identity, and per-target result contract.

The current Division/Jurisdiction generator remains upstream in `openstates/jurisdictions`. This repository does not duplicate that generator. Instead, an upstream execution adapter may supply structured results that are merged into the deterministic acceptance report.

This keeps the batch-first workflow honest:

1. Every requested target is represented.
2. Unsupported targets receive explicit exception classes.
3. Output hashes are computed from real generated artifacts.
4. A fixed run timestamp makes repeated reports reproducible.
5. No target is silently patched or dropped.

## PR 1 scope

PR 1 provides:

- a versioned target-manifest schema
- exact OCDID, explicit lookup, and alias-group selectors
- Batch Pilot 25 as a checked fixture
- a deterministic result-report schema
- an optional upstream execution-results overlay
- generated-artifact SHA-256 hashing
- CLI and unit tests

PR 1 does **not**:

- copy the upstream generator into this repository
- invent OCD IDs for lookup targets
- choose canonical aliases automatically
- claim that `not_run` targets were generated
- add target-specific classification rules

Those behaviors belong in an upstream adapter or later archetype-rule PRs.

## Manifest contract

Each target has:

| Field | Purpose |
|---|---|
| `target_id` | Stable acceptance-set identifier |
| `jurisdiction_name` | Human-readable target name |
| `state` | Two-letter state scope |
| `selector` | Explicit resolution instruction |
| `expected_archetype` | Archetype Registry identifier |
| `expected_classification` | Expected Jurisdiction classification |
| `category` | Regression fixture, known archetype, or discovery |

### Selector types

#### `ocdid`

The exact U.S. OCD division ID is already known.

#### `explicit_lookup`

The target requires a maintained override or authoritative lookup. Free-text fuzzy matching is not allowed.

#### `alias_group`

Multiple explicit divisions may correspond to one canonical jurisdiction. The manifest records the members and required canonical rule without silently selecting one.

## Upstream execution-results adapter

An upstream runner may write:

```json
{
  "version": 1,
  "results": {
    "BP25-001": {
      "match_status": "matched",
      "inferred_classification": "government",
      "classification_status": "matched",
      "generation_status": "generated",
      "division_paths": ["divisions/wa/local/seattle.yaml"],
      "jurisdiction_paths": ["jurisdictions/wa/local/seattle.yaml"],
      "exception_class": null,
      "review_reason": null,
      "human_minutes": 2.5
    }
  }
}
```

Only known target IDs and supported result fields are accepted. Generated artifact paths must be relative, remain inside the supplied artifact root, and exist before the report is written.

## Determinism

A run must receive a timezone-aware `run_asof`, either from the CLI or manifest.

The report identity is derived from:

- canonical manifest SHA-256
- execution-results SHA-256, when supplied
- normalized UTC `run_asof`
- ordered per-target results
- generated-artifact hashes

The same inputs and artifacts produce the same report and `run_id`.

## Baseline routing

Without upstream execution results:

| Selector | Match status | Exception |
|---|---|---|
| Exact OCDID | `resolved` | `upstream_execution_required` |
| Explicit lookup | `unresolved` | `explicit_lookup_required` |
| Alias group | `alias_group_pending` | `alias_resolution_required` |

This is intentional. The acceptance runner exposes what remains instead of overstating automation.

## Command

```bash
python scripts/run_target_manifest.py \
  --target-manifest tests/fixtures/batch_pilot_25.yml \
  --run-asof 2026-08-02T09:00:00-06:00 \
  --result-path build/batch_pilot_25.results.json
```

With upstream results:

```bash
python scripts/run_target_manifest.py \
  --target-manifest tests/fixtures/batch_pilot_25.yml \
  --execution-results build/upstream-results.json \
  --artifact-root path/to/jurisdictions-checkout \
  --run-asof 2026-08-02T09:00:00-06:00 \
  --result-path build/batch_pilot_25.results.json
```

## Implementation map

| Path | Responsibility |
|---|---|
| `schemas/target-manifest.schema.json` | Versioned input contract |
| `schemas/target-result-report.schema.json` | Versioned report contract |
| `tests/fixtures/batch_pilot_25.yml` | 25-target acceptance manifest |
| `civic_cartography/target_manifest.py` | Validation, normalization, overlays, hashing, reporting |
| `scripts/run_target_manifest.py` | CLI entry point |
| `tests/test_target_manifest.py` | Unit and contract tests |

Validation gates include:

- exactly 25 pilot targets
- exactly 14 states
- exactly 6 regression fixtures
- exactly 4 discovery targets
- unique target IDs
- explicit selector types only
- one result per target
- deterministic report identity
- contained, existing artifact paths

## Verification

```bash
python -m pytest -q
python -m compileall civic_cartography scripts
python scripts/run_target_manifest.py \
  --target-manifest tests/fixtures/batch_pilot_25.yml \
  --run-asof 2026-08-02T09:00:00-06:00 \
  --result-path /tmp/batch_pilot_25.results.json
```

Local verification before publishing: 9 tests passed, compile check passed, and the CLI emitted 25 deterministic result records.

## Deferred to PR 2

- six-fixture upstream execution harness
- classification and generated-path assertions against real upstream outputs
- two-run artifact checksum comparison
- fixture pass/fail roll-up

## Deferred to later capability PRs

- school-district lookup resolution
- special-district maintained overrides
- consolidated-government canonical alias rules
- reusable classification-rule additions
- median human-review reporting across completed runs
