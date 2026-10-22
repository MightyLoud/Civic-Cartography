# Kaufman Census provenance reconciliation — draft proposal

Based on the reviewed #483 integration tree `d3cf6380c3b7d4436dc123ef012a905af1f7960d`.

A fresh October 22 Census TIGERweb capture of GEOID 48257 preserves exact coordinates and stable source values. Verified vintage changes from 2025-01-01 to 2026-01-01, capture date from August 2 to October 22, AREALAND/AREAWATER digit strings become equal JSON integers, and volatile OBJECTID changes from 2732 to 2689. No geometric tolerance or coordinate normalization was used.

Original raw and canonical bytes are archived under `data/raw/kaufman-county/archive/2026-08-02/`. Only the Census manifest row and Census workflow capture date change. Commissioner geometry, derivation attribution, roster evidence and normalized records remain intact.

The combined canonical checksum changes because the county file contains changed metadata. Its exact new value is pinned in both the existing workflow and test; prior and proposed values are recorded in the verification evidence. The checksum gate remains strict.

Local validation: 253 tests passed; normalized validation passed for 33 files; GeoJSON joins and raw/canonical support passed. Eight live county-page contracts passed. Fresh Commissioner derivation produced four districts from all 37 voting precincts; raw/canonical/contract byte comparisons passed. Fresh Census comparison and the strict updated combined checksum passed. The statutes site returned wrapper content, so the existing validator retained its committed statutory evidence fallback. Combined GitHub CI is unverified.

This proposal is a draft, not merged or approved for production. No workflow was manually dispatched. Other jurisdictions remain independent. To reverse this bounded proposal, restore archived county files, prior Census date and original checksum together.
