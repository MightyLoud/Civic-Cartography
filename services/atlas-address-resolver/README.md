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


## Governance overlays

The county water layers contain both direct water providers and broader water-governance entities.

The resolver keeps these concepts separate:

- `provider_id` / `action_route_id`: only direct-service provider routing.
- `governance_overlays`: overlapping institutions that matter for water governance but are not the resident's tap-water utility.

Current non-retail overlay classes:

- Cheyenne Creek Metropolitan Park & Water District → `streamflow_water_rights_district`
- Southeastern Colorado Water Conservancy District → `regional_water_supply_authority`
- Upper Arkansas Water Conservancy District → `regional_augmentation_authority`
- Upper Big Sandy Ground Water Management District → `groundwater_regulator`
- Upper Black Squirrel Creek Ground Water Management District → `groundwater_regulator`

The live classification contract covers all 19 current raw county water-layer values. Direct-provider and non-retail-overlay classification are mutually exclusive.

Atlas governance for the same contract lives in `24_Water_Layer_Classification`.
