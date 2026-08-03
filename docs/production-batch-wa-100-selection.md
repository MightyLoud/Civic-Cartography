# Production Batch 1 Washington selection

This package freezes the deterministic selection for issue #112. It defines 100 active incorporated Washington municipal governments in five 20-target waves and preserves a 10-target replacement queue.

## Selection result

- Source workbook: `Nested_Divisions_Improved.xlsx`
- Workbook SHA-256: `dad097530321be8672f34ee6a9448ba4b19b362c80c70c7f6875141f229ebae4`
- Active incorporated municipalities: **281**
- Tracker-complete exclusions: **116**
- Eligible municipalities: **165**
- Production targets: **100**
- Replacement queue: **10**
- Eligible, not selected: **55**
- Unresolved tracker or maintained-OCDID matches: **0**

The unpublished interrupted calculation contained 111 tracker-complete exclusions. Before publication, Hatton, Hoquiam, Hunts Point, Ilwaco, and Index reached complete status in WA-012. This package was recomputed against the live tracker, producing **116 exclusions** and preventing duplicate work.

## Wave bounds

| Wave | IDs | First target | Last target |
|---|---|---|---|
| WA-PB01-A | 001–020 | Ione | Langley |
| WA-PB01-B | 021–040 | Latah | Mercer Island |
| WA-PB01-C | 041–060 | Mesa | Newport |
| WA-PB01-D | 061–080 | Nooksack | Pe Ell |
| WA-PB01-E | 081–100 | Pomeroy | Rosalia |

The replacement queue runs from **Roslyn** through **Sequim**.

## QA contract

- Every selected row resolves to exactly one maintained OCDID by Census GEOID.
- Target IDs and ordering are deterministic.
- All selected targets expect the `government` classification and AR-001 archetype.
- County, SLDU, and SLDL nesting values remain arrays; they are never flattened.
- Multi-county selected municipalities: Milton, Pacific.
- Selected targets with multiple SLDU or SLDL relationships: 16.
- The public crosswalk contains only the 100 targets and 10 replacements; private tracker identifiers and workflow details are not exported.
- Aggregate tracker reconciliation and the five removals from the unpublished draft remain in the source-selection manifest.

This PR freezes selection only. It does not commit generated Division or Jurisdiction YAML and does not claim officeholder-roster completion.
