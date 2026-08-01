# Olmos Park, Texas Pilot

## Scope

This pilot maps one jurisdiction end to end: the City of Olmos Park, Texas.

Olmos Park uses a Mayor and five City Council places. Every position is elected at-large, so the map-ready geography is one citywide feature rather than six invented district polygons.

## Identifiers

| Field | Value |
|---|---|
| State FIPS | `48` |
| Census place FIPS | `53988` |
| Census GEOID | `4853988` |
| Canonical record ID | `TX:municipality:olmos-park:at_large:CITYWIDE` |
| Geometry ID | `olmos-park-citywide` |

## Sources

1. City election page: election scope, candidate filings, the Place 4 withdrawal, unopposed certification, cancellation, and at-large structure.
2. City Council page: Mayor plus five council members and current term dates.
3. U.S. Census TIGERweb Incorporated Places layer: January 1, 2025 municipal boundary.

See `data/raw/olmos-park/source-manifest.csv` for exact source URLs, retrieval date, authority, and usage.

## Transformations

- Four filing events are retained in raw data.
- Adam Harden's withdrawal remains in raw history but is not treated as a final candidate or officeholder.
- The three remaining 2026 candidates were certified unopposed.
- The citywide geography is represented by one normalized record and one GeoJSON feature.
- GeoJSON is generated from the official Census service using GEOID `4853988`, then receives stable repository join properties.

## QA and parity

| Gate | Result |
|---|---:|
| Raw candidate filing rows | 4 |
| Raw Census boundary features | 1 |
| Normalized geography rows | 1 |
| Map-ready GeoJSON features | 1 |
| Missing geometry joins | 0 |
| Extra geometry joins | 0 |
| Normalized `qa_status` | `approved` |
| Normalized `parity_ok` | `TRUE` |

## Reproduce

```bash
python scripts/fetch_tigerweb_place.py \
  --geoid 4853988 \
  --record-id TX:municipality:olmos-park:at_large:CITYWIDE \
  --geometry-id olmos-park-citywide \
  --retrieved-at 2026-08-01 \
  --raw-output data/raw/olmos-park/tigerweb-incorporated-place-4853988.geojson \
  --output data/geojson/olmos_park_citywide.geojson

pytest -q
python scripts/validate.py
python scripts/validate_geojson.py
```

## Known limitations

- The boundary is the Census January 1, 2025 vintage; later annexations or detachments require a refreshed fetch.
- This pilot proves jurisdiction and citywide map parity. It does not yet model Person and Role_Term entities as separate canonical tables.
