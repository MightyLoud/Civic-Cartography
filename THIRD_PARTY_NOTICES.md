# Third-party dependency notice

This notice records the dependencies and workflow actions used by the
LIC-G5 hardening change. It does not change the license of this repository
and is not a legal compatibility determination.

## Python dependency set

Exact versions and integrity hashes are retained in `requirements-dev.lock`.
The machine-readable inventory is retained in `sbom.cdx.json`.

| Dependency | Version | Provider license metadata |
| --- | ---: | --- |
| pytest | 8.4.2 | MIT |
| PyYAML | 6.0.3 | MIT |
| jsonschema | 4.26.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| Pillow | 12.3.0 | MIT-CMU |
| pyproj | 3.7.2 | MIT |
| pyshp | 3.1.6 | MIT |
| shapely | 2.1.2 | BSD-3-Clause |
| uv | 0.11.33 | MIT OR Apache-2.0 |

`PyMuPDF` is intentionally excluded. The frozen workflows installed it in
three jobs, but repository code did not import `fitz` or `pymupdf`.
Removing the unused install avoids carrying its AGPL-3.0/commercial-license
choice into this dependency set.

Transitive components and package URLs are listed in `sbom.cdx.json`.
Provider license metadata should be rechecked during dependency upgrades.

## GitHub Actions

| Action | Pinned commit | License |
| --- | --- | --- |
| actions/checkout | `11d5960a326750d5838078e36cf38b85af677262` | MIT |
| actions/setup-python | `a26af69be951a213d495a4c3e4e4022e16d87065` | MIT |
| actions/upload-artifact | `ea165f8d65b6e75b540449e92b4886f43607fa02` | MIT |

The comments beside each workflow reference preserve the prior major-tag
context while the executable reference is a full commit SHA.

## Patched OpenStates upstream

Some workflows use `openstates/jurisdictions` at commit
`6fbe7d6aed32c3b781490c8e4c5a737bdd6e4705`, apply local patches, and run
its frozen `uv.lock`. That upstream is licensed under GNU AGPL v3.

This control records the source, pin, and license. Before distributing
patched upstream code or a combined product, retain a separate reviewed
obligation/attribution determination. CI use and derived data outputs are
not classified by this notice.

## Build-input provenance

The repository's jurisdiction workflows already retain source snapshots and
release digests for governed outputs. Any new build-relevant network input
must add an immutable snapshot or expected digest and fail closed on
mismatch before LIC-G5 can be reconsidered.
