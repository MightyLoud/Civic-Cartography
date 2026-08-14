# Third-party dependency notice

This notice records the dependencies and workflow actions used by the
LIC-G5 hardening change. It does not change the license of this repository
and is not a legal compatibility determination.

## Python dependency set

Exact versions and integrity hashes are retained in `requirements-dev.lock`.
The complete direct and transitive machine-readable inventory is retained in
`sbom.cdx.json`; exact-head CI also retains the installed package license files.

| Direct dependency | Version | Provider license metadata |
| --- | ---: | --- |
| pytest | 9.1.1 | MIT |
| PyYAML | 6.0.3 | MIT |
| jsonschema | 4.26.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| Pillow | 12.3.0 | MIT-CMU |
| pyproj | 3.7.2 | MIT |
| pyshp | 3.1.6 | MIT |
| shapely | 2.1.2 | BSD-3-Clause |
| uv | 0.11.33 | MIT OR Apache-2.0 |
| pypdfium2 | 5.12.1 | Apache-2.0 OR BSD-3-Clause, plus bundled PDFium dependency licenses |
| pip-audit | 2.9.0 | Apache-2.0 |
| pip-tools | 7.5.1 | BSD |
| pip-licenses | 5.5.5 | MIT |

`PyMuPDF` is intentionally excluded because it is offered under an
AGPL-3.0/commercial-license choice. Two historical derivation scripts import
`fitz`; this branch retains that narrow API through local compatibility shims
backed by `pypdfium2`, not PyMuPDF. The pypdfium2 wheels bundle PDFium and
third-party license files; those bundled notices remain part of the installed
package evidence and must be retained when redistributing the binary package.

Provider license metadata should be rechecked during dependency upgrades.
No dependency license is treated as a root Civic-Cartography license.

## GitHub Actions

| Action | Pinned commit | License |
| --- | --- | --- |
| actions/checkout | `11d5960a326750d5838078e36cf38b85af677262` | MIT |
| actions/setup-python | `a26af69be951a213d495a4c3e4e4022e16d87065` | MIT |
| actions/upload-artifact | `ea165f8d65b6e75b540449e92b4886f43607fa02` | MIT |

The comments beside workflow references preserve the prior major-tag context
while each executable reference is a full commit SHA.

## Patched OpenStates upstream

Some workflows use `openstates/jurisdictions` at commit
`6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`, apply local patches, and run
its frozen `uv.lock`. That upstream is licensed under GNU AGPL v3.

This control records the source, pin, and license. Before distributing patched
upstream code or a combined product, retain a separate reviewed obligation and
attribution determination. CI use and derived data outputs are not classified
by this notice.

## Build-input provenance

The repository's jurisdiction workflows retain source snapshots, expected
hashes, or governed live-source contracts for release evidence. Any new
build-relevant network input must add an immutable snapshot, expected digest,
or explicit fail-closed source contract before LIC-G5 can be reconsidered.

## Authority boundary

This notice and the supply-chain controls do not create a repository license,
publication authority, reuse authority, transfer authority, release authority,
or implementation authority.
