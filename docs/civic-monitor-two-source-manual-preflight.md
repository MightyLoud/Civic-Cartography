# Two-source monitoring: manual HTTPS connectivity preflight

**Review only. Not a production monitor.** This public-repository branch contains a self-contained, manual-only preflight for the two pinned official sites:

- `SRCMON-006` — Cuyahoga County: `https://cuyahogacounty.gov/code/roster-of-officials`
- `SRCMON-007` — Cook County: `https://www.cookcountyil.gov/all-people`

## Boundaries

- Trigger: `workflow_dispatch` only, with `acknowledge_readonly=true` explicitly required; not dispatched as part of the draft pull request.
- Token permission: `contents: read`; no repo credentials are persisted.
- HTTPS GET only, exact hosts and same-host HTTPS redirects, 20-second timeout, 4 MiB maximum response, HTML and HTTP-200 requirement.
- No raw HTML, names, source bodies or headers logged or uploaded. Only high-level success/failure classes.
- No schedule, Sheets/Gmail API use, source record writes, event creation, date/cursor advancement, or publication.
- `GATE-CM-006=WAIT` regardless of result.

## Important scope distinction

The complete **v0.5 two-county runner package** is separately staged in the conversation as `Civic_Data_Two_Source_GitHub_Manual_v0_5.zip`. This PR **does not yet include its complete raw-HTML parsers, 40-office crosswalk, offline tests or checksum manifest**. It includes an independently usable *connectivity preflight only*, to keep the review diff small and avoid presenting a partially transferred full runner as production-ready.

An HTTP_OK here means the public runner received bounded HTML bytes; it does not prove 40-office roster coverage, historical hash compatibility, independent QA or unattended monitoring. Before any full monitoring-runner PR or production activation, separately review and incorporate the complete pinned package, independently preserve raw evidence, and maintain `GATE-CM-006=WAIT` until every operational gate is satisfied.

The destination repository is public. This preflight deliberately publishes no raw county-page snapshots as Actions artifacts.
