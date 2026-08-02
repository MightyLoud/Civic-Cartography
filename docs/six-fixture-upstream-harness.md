# Six-fixture upstream regression harness

Issue: #43  
Depends on: PR #47

## Purpose

The target-manifest runner records one result per requested jurisdiction. This
harness turns the six validated jurisdictions into a strict regression gate.
It compares two reports created from the same manifest, timestamp, upstream
revision, execution inputs, and generated artifacts.

The gate passes only when all six fixtures:

1. resolve to at least one OCD division ID;
2. infer the classification declared in `batch_pilot_25.yml`;
3. generate at least one Division and one Jurisdiction artifact;
4. have hashes covering every reported artifact path;
5. carry no unresolved exception or review reason;
6. produce identical results and artifact hashes on the second run; and
7. have a median recorded human-review time of ten minutes or less.

A non-generated fixture is not hidden. Its exception class and review reason
remain in the evaluation output, and the command exits with status 1.
Malformed inputs exit with status 2.

## Upstream evidence boundary

The evaluator requires a pinned 40-character upstream commit SHA. It does not
fetch mutable branches and it does not generate substitute fixture YAML.

During implementation, the pinned upstream tree
`openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`
contained committed sample outputs for Seattle and Tacoma, including:

- `tests/sample_output/jurisdictions/test/wa/local/seattle_city_government_bd405187-c499-5b44-aee8-3800784ee617.yaml`
- `tests/sample_output/divisions/test/wa/local/tacoma_a82e350d-72bb-5b02-8375-b66c9d2b6126.yaml`
- `tests/sample_output/jurisdictions/test/wa/local/tacoma_city_government_1c2a18a9-a8e3-586d-9968-502e8abb102e.yaml`

A complete, committed six-fixture upstream capture was not located in that
pinned tree. Therefore this PR supplies the executable gate, schema, and test
coverage without claiming that the real 6/6 upstream acceptance run has
already passed. The real gate remains red until two complete upstream reports
are supplied.

## Required upstream run inputs

For each of two runs, an upstream adapter must produce:

- the same Batch Pilot 25 manifest;
- the same timezone-aware `run_asof` value;
- one execution-result overlay per attempted target;
- generated Division and Jurisdiction files under an artifact root; and
- explicit exception classes and review reasons for anything not generated.

Use the PR #47 runner to turn each upstream capture into a deterministic report:

```bash
python scripts/run_target_manifest.py \
  --target-manifest tests/fixtures/batch_pilot_25.yml \
  --run-asof 2026-08-02T15:00:00Z \
  --execution-results build/run-1/execution-results.json \
  --artifact-root build/run-1/artifacts \
  --result-path build/run-1/report.json
```

Repeat with a clean `build/run-2` directory and the same timestamp. Then run:

```bash
python scripts/check_regression_fixtures.py \
  --target-manifest tests/fixtures/batch_pilot_25.yml \
  --first-report build/run-1/report.json \
  --second-report build/run-2/report.json \
  --upstream-repository openstates/jurisdictions \
  --upstream-revision <40-character-commit-sha> \
  --result-path build/fixture-evaluation.json
```

## Output

The versioned evaluation report contains:

- pinned upstream repository and revision;
- the two run IDs;
- one outcome for each regression fixture;
- classifications, generated paths, hashes, exceptions, and review time;
- fixture and determinism counts; and
- the final `gate_passed` decision.

The output must validate against
`schemas/regression-fixture-report.schema.json`.
