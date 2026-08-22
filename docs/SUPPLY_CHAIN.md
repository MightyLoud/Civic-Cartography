# Supply-chain status (D-137)

This repository pins GitHub Actions to full commit SHAs and pins every direct
Python input used by CI to an exact version. The enforcement control is
`python scripts/check_supply_chain_pins.py`.

LIC-G5 is not closed by this change. Closure still requires:

1. a transitive dependency lock with integrity hashes;
2. a machine-readable SBOM generated from a clean environment;
3. clean-CI installation and test evidence from that lock;
4. documented obligation treatment for PyMuPDF (AGPL-3.0-or-later or commercial)
   and the pinned OpenStates Jurisdictions upstream (AGPL-3.0);
5. recorded build-input digests.

Until those controls pass, D-137 and LIC-G5 remain OPEN.
