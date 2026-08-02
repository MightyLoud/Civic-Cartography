# Real upstream six-fixture baseline

Issue: #43  
Pull request: #51  
Capture date: 2026-08-02

## Pinned execution

- Upstream repository: `openstates/jurisdictions`
- Upstream revision: `6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`
- Run timestamp: `2026-08-02T15:00:00Z`
- Workflow run: `30757656085`
- Evidence artifact: `8836443045`
- Evaluation ID: `e7e19c6a64e4527b8117`
- First run ID: `f9aa6a4006b57d6d9c80`
- Second run ID: `f9aa6a4006b57d6d9c80`

The two captures used clean output directories, the same pinned upstream code,
the same timestamp, and the same downloaded source bytes. The source files and
SHA-256 hashes are recorded in
[`source-manifest.json`](../evidence/upstream-six-fixture/2026-08-02/source-manifest.json).
The full gate output is recorded in
[`fixture-evaluation.json`](../evidence/upstream-six-fixture/2026-08-02/fixture-evaluation.json).

## Result

| Fixture | Result | Generation | Explicit outcome |
|---|---|---|---|
| Seattle | Passed | Division and Jurisdiction generated | None |
| Tacoma | Passed | Division and Jurisdiction generated | None |
| Pierce County | Failed | Division only | `upstream_partial_generation` |
| Colorado Springs School District 11 | Failed | Division only | `upstream_partial_generation` |
| Regional Transportation District | Failed | Not generated | `upstream_target_not_found` |
| City and County of Denver | Failed | Place member complete; county member partial | `upstream_partial_generation` |

Gate summary:

- Fixtures passed: **2/6**
- Deterministic fixtures: **6/6**
- Complete report equality: **passed**
- Median recorded human review: **0 minutes**
- Overall gate: **failed**

This is a useful result. The system now has a reproducible baseline and the
failures fall into reusable classes rather than six unrelated target patches.

## What passed

### Seattle and Tacoma

Both municipal-place fixtures:

1. resolved through explicit OCD division IDs;
2. matched one validation record;
3. inferred `government`;
4. generated both Division and Jurisdiction YAML; and
5. produced identical paths and SHA-256 hashes on the second run.

The municipal-place archetype is therefore a working regression fixture at the
pinned upstream revision.

## Reusable gaps exposed

### 1. No-validation-match records stop before jurisdiction classification

Pierce County and Colorado Springs School District 11 both resolve to real OCD
division IDs, but `GeneratePipeline.run()` finds no validation record. The
current branch creates a stub Division, marks the response partial, and returns
before calling `infer_jurisdiction_seed`.

That prevents the OCD division type itself from producing the expected
`government` or `school_system` Jurisdiction.

**Required generator change:** continue reusable jurisdiction classification
after stub Division creation instead of treating missing validation enrichment
as a reason to stop generation entirely.

### 2. Empty LSAD blocks otherwise valid OCD-type classification

The diagnostic classifier call for the stub county and school-district records
receives an empty LSAD and raises `Unknown LSAD code ''`. The OCD division path
already contains enough information to identify `county` or `school_district`.

**Required generator change:** normalize empty LSAD values to absent values and
allow the OCD division type to drive classification when validation metadata is
unavailable.

These first two changes should repair both Pierce County and District 11 through
one generalized code path.

### 3. RTD has no resolvable OCD division record

The maintained exact-name aliases for Regional Transportation District did not
match any record in the captured national, Washington, or Colorado OCD inputs.
No fuzzy match or synthetic production record was introduced.

**Required data/model change:** establish an authoritative maintained identifier
or override for RTD, then route that division through the existing
`transit_authority` classification. This should be a reusable special-district
mechanism, not an RTD-only generator branch.

### 4. Consolidated alias groups need one canonical generation result

For City and County of Denver, the place member generated successfully while
the county member followed the same stub-only failure as Pierce County. The
fixture correctly remained partial because the alias rule has not selected one
canonical result.

**Required selection change:** evaluate the maintained alias group before
acceptance and designate a canonical generated jurisdiction, while preserving
both OCD division members as aliases. The gate should not require two competing
Jurisdiction records for one consolidated government.

## Recommended implementation order

1. Continue classification and Jurisdiction generation after a stub Division.
2. Treat empty LSAD as missing and classify from the OCD division type.
3. Rerun the same six fixtures; Pierce County and District 11 should move first.
4. Add canonical alias handling and rerun Denver.
5. Add the reusable special-district identifier/override path and rerun RTD.
6. Rerun the unchanged Batch Pilot 25 manifest.

The operating rule remains unchanged:

> No handcrafted jurisdiction seven. Improve the generator, then rerun the same
> targets.
