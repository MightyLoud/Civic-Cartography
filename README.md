# Civic Cartography

Civic Cartography is a working repository for turning sourced civic data into validated, map-ready datasets.

## MVP pipeline

```text
Source files and official pages
        ↓
data/raw
        ↓
Normalization
        ↓
data/normalized
        ↓
Automated QA and parity validation
        ↓
data/geojson
        ↓
Interactive civic maps
```

## Definition of done

A civic-data batch is complete only when:

1. The raw source is preserved or referenced.
2. A normalized dataset exists.
3. Automated and manual QA are complete.
4. `parity_ok` is `TRUE` for every published record.
5. The external operations tracker reflects completion.

## Repository layout

- `data/raw/` — immutable source extracts and source notes.
- `data/normalized/` — standardized CSV datasets ready for validation.
- `data/geojson/` — generated map-ready GeoJSON.
- `docs/` — schemas, methods, and QA rules.
- `scripts/` — import, normalization, validation, and export utilities.
- `tests/` — automated tests for the data pipeline.
- `.github/workflows/` — continuous validation in GitHub Actions.

## Local validation

```bash
python -m pip install -r requirements-dev.txt
pytest
python scripts/validate.py
```

The validator scans CSV files in `data/normalized/`. It exits successfully when the directory contains no datasets, allowing the repository scaffold to pass before the first import.

## Current status

Initial project scaffold. The next milestone is importing one jurisdiction end to end: raw source → normalized CSV → QA → GeoJSON.
