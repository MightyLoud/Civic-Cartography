# Atlas Address Resolver

Small HTTP service for Civic Atlas address → water-provider routing.

## Endpoints

- `/health`
- `/resolve.json?address=...`
- `/resolve.csv?address=...`
- `/selftest.json`

The CSV endpoint is designed for Google Sheets `IMPORTDATA`.

## Resolution order

1. U.S. Census geocode.
2. El Paso County sanitation/water district polygon.
3. El Paso County water district polygon.
4. Colorado Springs Utilities Water Boundary.
5. Fail closed as `UNRESOLVED`.

A Colorado Springs mailing address is **not** treated as proof of CSU water service.

## Regression controls

The service runs these on startup and logs `SELFTEST {...}` records:

- 2855 Mesa Road → Colorado Springs Utilities
- 13631 Shepard Hts → Donala WSD
- 6310 Highway 85-87 → Security WSD
- 2586 Soma View → unresolved

## Run locally

```bash
python app.py
```
