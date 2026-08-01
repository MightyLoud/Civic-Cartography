# Validation and QA Contract

Validation is the publication gate between normalized civic records and map-ready outputs.

## Automated checks

The validator fails a dataset when it finds any of the following:

- A required column is missing.
- A required field is blank.
- `record_id` is duplicated within the validation run.
- `state_fips` is not exactly two digits.
- `state_abbr` is not exactly two uppercase letters.
- `jurisdiction_type` is outside the approved vocabulary.
- `source_url` is not an HTTP or HTTPS URL.
- `source_retrieved_at` is not a valid `YYYY-MM-DD` date.
- `source_confidence` is not `high`, `medium`, or `low`.
- `qa_status` is not `pending`, `reviewed`, or `approved`.
- `parity_ok` is not `TRUE`.

## Manual QA checklist

Before setting `parity_ok` to `TRUE`, confirm:

- [ ] Raw evidence exists or the source URL is durable and direct.
- [ ] Names and identifiers match the source.
- [ ] Parent jurisdiction and district relationships are correct.
- [ ] Counts match the authoritative source.
- [ ] Geometry joins have no missing or duplicate records.
- [ ] Known exceptions are documented in `notes`.
- [ ] Another reviewer could reproduce the result from the cited source.

## Parity definition

`parity_ok = TRUE` means the normalized dataset, geometry, and source evidence agree at the level required for publication. It is not merely a signal that a CSV loaded without errors.

At minimum, parity requires:

1. Record-count agreement or a documented reason for a difference.
2. Unique and complete joins between normalized records and mapped features.
3. No unresolved low-confidence records in the publication set.
4. Approved QA status for every published record.

## Failure handling

Do not patch downstream GeoJSON to hide an upstream data problem. Correct the raw-to-normalized transformation, rerun validation, regenerate map outputs, and update the operations tracker only after the full chain passes.
