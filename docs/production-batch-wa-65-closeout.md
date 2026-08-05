# Production Batch 2 — Washington 65-target closeout

Production Batch 2 covers the final 65 frozen active Washington municipal governments, WA-PB02-001 through WA-PB02-065, Roslyn through Zillah.

## Machine-verified result

- Waves passed: **4/4**
- Targets resolved by exact maintained OCDID: **65/65**
- `government` classifications: **65/65**
- Division + Jurisdiction generation: **65/65**
- Deterministic targets across two captures per wave: **65/65**
- List-valued county/SLDU/SLDL nesting parity: **65/65**
- Target artifacts hashed: **130/130**
- Wave-scoped shared ancestor-stub hash entries: **8/8**
- Total artifact hash entries: **138/138**
- Exceptions or review reasons: **0**
- Target-only production patches: **0**
- Frozen Batch Pilot regression retained: **25/25**

The eight shared-artifact hash entries are the same two Washington ancestor-stub paths inventoried independently in each of the four waves; they are not eight unique shared files.

Roll-up ID: `2ae72ee3e5b6cdcc203c`

## Evidence chain

The final roll-up hashes and evaluates each committed wave acceptance record. Every wave uses the same 65-target selection crosswalk and pinned upstream revision:

`openstates/jurisdictions@6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`

The roll-up enforces exact IDs 001–065, rejects duplicate or missing targets, verifies two target artifact hashes per jurisdiction, and requires every wave criterion and inventory gate to pass.

## Washington generator completion

The 116 municipalities completed before Production Batch 1, Production Batch 1's 100 targets, and Production Batch 2's 65 targets together establish **281/281** Washington municipal Division/Jurisdiction generator coverage.

This closes the generator and nesting workstream only. It does not claim completion of the separate officeholder-roster workflow.

## Release closeout

The repository evidence satisfies the internal 65-target completion contract. Final-head workflow status and the scoped operations-tracker update are recorded on PR #139 and issue #134 after the release head passes.
