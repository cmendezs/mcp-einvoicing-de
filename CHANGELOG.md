# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.11.4] - 2026-09-12

### Changed
- Lower-bound pin on `mcp-einvoicing-core` raised to `>=1.34.1` (was `>=1.21.0`). This package's own CI now runs `CHECK_PUBLIC_HYGIENE`, the pre-publish audit check that blocks accidental citations of the private orchestration repo.

---

## [0.11.3] - 2026-09-07

### Fixed
- **`src/mcp_einvoicing_de/__init__.py`'s `__version__` was left at `0.11.1`**
  across the v0.11.2 release, while `pyproject.toml` and `server.json` were
  both bumped correctly. Purely a metadata fix; no behavioral change.

### Added
- `tests/test_metadata.py::test_version_slot_consistency` — regression test
  guarding all three version slots against future drift.

---

## [0.11.2] - 2026-09-07

### Fixed
- **XRechnung CII validation no longer rejects every invoice.** The local `XRECHNUNG` CII validation chain used FeRD's `FACTUR-X_EN16931.xslt` as its EN 16931 base, which enforces the Factur-X BT-24 codelist and fails the XRechnung profile URN (`FX-SCH-A-000556`) — so every XRechnung CII invoice was reported invalid. The genuine CEN `EN16931-CII-validation.xsl` is now bundled and used as the CII base (new stylesheet key `en16931_cii_cen`).

### Changed
- **Bundled XRechnung rules are now a single version-matched set.** The EN 16931 base (UBL + CII) and the XRechnung 3.0.2 CIUS overlay (UBL + CII) are all sourced from the `validator-configuration-xrechnung` v2026-08-31 release, replacing the earlier split (base v2026-01-31 + CIUS from `xrechnung-schematron` v2.6.0) that had drifted out of sync.

### Added
- Vendored the official KoSIT `xrechnung-testsuite` v2026-08-31 positive reference corpus (Apache-2.0) under `specs/xrechnung/testsuite/`, and a new `tests/test_xrechnung_testsuite.py` that validates all 78 standard + CIUS instances clean through the `XRECHNUNG` chain (the `extension`/`cvd` instances are separate XRechnung profiles and are xfailed by design). This corpus is what surfaced the CII fix above.

---

## [0.10.0] - 2026-08-24

### Changed
- **`peppol_send` now emits a real `wsse:Security` message signature.** `mcp-einvoicing-core` v1.20.0 fixed the AS4 transport client's `_apply_message_signature`, which previously computed a signature and discarded it, sending unsigned outbound messages. This is an API-compatible, wire-level behavior change — no code in this package changed to pick it up, but every outbound message sent through this package's `peppol_send` is now actually signed. **Not yet validated against a live sandbox Peppol AP**; treat as unverified at the transport level until that validation runs.
- Lower-bound pin on `mcp-einvoicing-core` raised to `>=1.20.0` (was `>=1.19.0`).
- `xslt2` extra now also chains `mcp-einvoicing-core[xslt2]>=1.20.0` alongside the existing direct `saxonche` pin, so both this package's own Factur-X/XRechnung stylesheets and core's new Peppol EUSR/TSR/MLS validators resolve consistently.

### Added
- Mounted three new opt-in core plugins in `server.py`, alongside the existing Peppol tool plugin:
  - `register_peppol_reporting_tools` (`mcp_einvoicing_core.peppol.reporting_tools`) — `validate_eusr_report`, `validate_tsr_report` (End User / Transaction Statistics Reports). Requires the `[xslt2]` extra.
  - `register_peppol_mls_tools` (`mcp_einvoicing_core.peppol.mls_tools`) — `validate_mls_message`, `build_mls_message` (Message Level Status). Requires the `[xslt2]` extra.
  - `register_en16931_codelist_tools` (`mcp_einvoicing_core.en16931_codelist_tools`) — 13 `list_*`/`check_*` pairs plus `get_en16931_codelist_version` for the EN 16931 semantic code lists. Requires `EINVOICING_EN16931_CODELIST_DIR` to be set to a local copy of the CEF Digital code lists (not bundled).
  - `peppol_directory_search` (public Peppol Directory search) arrives automatically via the existing `register_peppol_tools` mount — no `server.py` change needed for this one.
- All new tools are mounted unconditionally; they raise a clear error at call time (not at registration) when their extra or data directory is missing, matching the existing eDEC codelist tool pattern.

---

## [0.9.0] - 2026-08-22

### Added
- Initial changelog. Prior release history is recorded in the Git tags and
  GitHub Releases for this repository.
