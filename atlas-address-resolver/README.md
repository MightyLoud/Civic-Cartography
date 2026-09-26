# Atlas Address Resolver

Live address → water service-area → provider resolver for the Civic Atlas.

## Endpoints

- `GET /health`
- `GET /resolve.json?address=2855%20Mesa%20Road%2C%20Colorado%20Springs%2C%20CO%2080904`
- `GET /resolve.csv?address=...` — designed for Google Sheets `IMPORTDATA`.

## Resolution order

1. U.S. Census geocoder.
2. El Paso County sanitation/water district polygon.
3. El Paso County water district polygon.
4. Colorado Springs Utilities Water Boundary.
5. Fail closed as `UNRESOLVED`.

A Colorado Springs mailing address never implies CSU by itself.

## Atlas integration

The resolver returns normalized Atlas IDs including:

- provider_id
- service_area_ref_id
- service_area_route_id
- action_route_id

The registered Atlas workbook uses the CSV endpoint from `23_Live_Address_Resolver`.
