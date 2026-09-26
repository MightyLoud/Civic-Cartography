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


## Specialized governance routes

Non-retail water-governance overlays can expose their own `action_route_id` inside `governance_overlays` without replacing the retail provider fields.

Current specialized routes:

- Cheyenne Creek Metropolitan Park & Water District → `action_cheyenne_creek_streamflow_governance_inquiry`
- Southeastern Colorado Water Conservancy District → `action_secwcd_project_water_allocation`
- Upper Arkansas Water Conservancy District → `action_uawcd_augmentation_application`
- Upper Big Sandy Ground Water Management District → `action_upper_big_sandy_groundwater_regulatory_inquiry`
- Upper Black Squirrel Creek Ground Water Management District → `action_upper_black_squirrel_groundwater_regulatory_inquiry`

Safety contract:

- `provider_id` and top-level `action_route_id` remain reserved for direct retail service.
- Overlay routes appear only inside `governance_overlays`.
- SECWCD allocation routing is eligibility- and annual-cycle-gated; it does not imply an application window or Project Water availability is always open.
- Groundwater-management routes provide District-level regulatory guidance and do not pretend the districts are retail utilities or the State's well-permit issuing authority.


## Human issue classifier

The resolver can classify a plain-language water problem separately from location/provider resolution.

Pass the issue text as:

```
/resolve.json?address=...&issue=My%20water%20is%20out
```

Classifier outputs:

- `issue_type`
- `issue_route_id`
- `issue_route_source` (`provider` or `governance_overlay`)
- `issue_classifier_status`
- `issue_route_candidates`

Current canonical issue types:

- `water_service_interruption` → direct provider Action Route
- `groundwater_regulatory_question` → groundwater-regulator overlay route
- `augmentation_water_need` → regional augmentation overlay route
- `project_water_allocation` → regional project-water overlay route
- `cheyenne_creek_governance` → Cheyenne Creek governance overlay route

Fail-closed statuses include:

- `NEEDS_LOCATION`
- `LOCATION_UNRESOLVED`
- `PROCESS_BLOCKED`
- `NO_APPLICABLE_ROUTE`
- `AMBIGUOUS`
- `UNSUPPORTED`

The issue classifier never overwrites the underlying `provider_id`, top-level provider `action_route_id`, or `governance_overlays`.


## Cross-domain civic issue routing

The resolver now supports both spatial issues and institution-first civic issues.

### Institution-first routes
These do not require an address when the responsible institution is explicit in the issue text:

- Colorado Springs ADA / public-program accessibility → `action_cos_accessibility_public_program`
- Colorado Springs public records / CORA → `action_cos_public_records_general`

Generic wording such as "I need public records" or "I need an ADA accommodation" fails closed with `NEEDS_INSTITUTION` rather than assuming Colorado Springs.

### Spatial routes
Water issues continue to use the existing address/provider/governance-overlay resolver.

The classifier output includes:

- `issue_domain`
- `issue_type`
- `issue_route_id`
- `issue_route_source`
- `issue_classifier_status`
- `issue_route_candidates`

This allows the same endpoint to route institution-based and location-based civic problems without changing the underlying provider or governance models.


## Transportation service routing

The cross-domain classifier includes a location-gated Colorado Springs pothole / street-surface rule.

- Issue type: `pothole_or_street_surface_defect`
- Action Route: `action_cos_pothole_report`
- Route source: `institution`
- Spatial gate: the address/point must resolve inside the Colorado Springs incorporated-place polygon.
- Missing location → `NEEDS_LOCATION`
- Outside Colorado Springs place boundary → `NO_APPLICABLE_ROUTE`

The municipal-boundary gate is only an intake-routing control. It does not assert that every roadway inside the boundary is City-maintained; the City intake process may triage state, private, or other non-City roadway issues.


## Municipal service-request cohort

The cross-domain classifier now supports additional Colorado Springs location-gated City services:

- Traffic signal / sign issue → `action_cos_traffic_signal_sign_report`
- Clogged storm drain / drainage maintenance → `action_cos_storm_drain_maintenance`
- Streetlight outage / damage → `action_cos_streetlight_maintenance`

All three require a resolvable point inside the Colorado Springs incorporated-place polygon.

Fail-closed behavior:
- missing location → `NEEDS_LOCATION`
- outside Colorado Springs → `NO_APPLICABLE_ROUTE`

The municipal boundary is an intake-routing control, not proof of City ownership/maintenance responsibility for every road, asset, or drainage structure.


## Neighborhood and code-enforcement routing

The civic classifier distinguishes four location-gated Colorado Springs neighborhood/enforcement patterns:

- Private-property / neighborhood nuisance → `action_cos_code_enforcement_complaint`
- Non-emergency environmental dumping / illicit discharge → `action_cos_illicit_discharge_report`
- Abandoned or inoperable vehicle on a City street/right-of-way → `action_cos_abandoned_street_vehicle_report`
- General public-space trash / illegal dumping → `action_cos_public_space_dumping_report`

Precedence matters. Stormwater/environmental dumping language is evaluated before generic public-space dumping so environmental discharges do not fall into the cleanup-only route. Private-property inoperable vehicles stay in the property nuisance route, while abandoned street/right-of-way vehicles use the specific vehicle route.

All four require a resolvable point inside the Colorado Springs incorporated-place polygon:
- missing location → `NEEDS_LOCATION`
- outside Colorado Springs → `NO_APPLICABLE_ROUTE`

Emergency/hazardous spills, active crimes, and immediate hazards remain outside these non-emergency routes.


## Neighborhood and code-enforcement cohort

The cross-domain classifier includes four Colorado Springs location-gated neighborhood/enforcement routes:

- Private-property / neighborhood code nuisance → `action_cos_code_enforcement_complaint`
- Non-emergency illicit discharge / environmental dumping → `action_cos_illicit_discharge_report`
- Generic public-space trash / illegal dumping → `action_cos_public_space_dumping_report`
- Abandoned vehicle on a City street / right-of-way → `action_cos_abandoned_street_vehicle_report`

Classifier precedence is intentional:

1. Environmental/stormwater dumping language wins over generic illegal dumping.
2. Private-property vehicle/property nuisance language routes to general Neighborhood Services code enforcement.
3. Abandoned street-vehicle language routes to the specific 72-hour street/right-of-way process.
4. Generic public-space trash/dumping falls back to GoCOS City intake for downstream triage.

All four require a resolved point inside the Colorado Springs incorporated-place polygon. Missing location fails with `NEEDS_LOCATION`; outside-city locations fail with `NO_APPLICABLE_ROUTE`.

## Animal services / contracted-delivery cohort

Colorado Springs animal-control delivery is modeled as a contracted-service pattern: the City retains the route scope while Humane Society of the Pikes Peak Region (HSPPR) Animal Law Enforcement is the operational service actor.

Current location-gated routes:

- Animal cruelty, neglect, dog bite/attack, or animal distress → `action_cos_animal_cruelty_distress_report`
- Stray, found, injured, or aggressive domestic animal → `action_cos_stray_found_aggressive_animal`
- Colorado Springs dog/cat licensing → `action_cos_pet_license`

All three require a resolved point inside the Colorado Springs incorporated-place polygon:

- missing location → `NEEDS_LOCATION`
- outside Colorado Springs → `NO_APPLICABLE_ROUTE`

Wildlife is excluded from the domestic-animal routes. The Atlas actor record explicitly represents HSPPR as an external contracted service actor and does not imply City ownership of the nonprofit.
