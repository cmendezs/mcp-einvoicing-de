# Release Process for mcp-einvoicing-de

This document describes how to release a new version of `mcp-einvoicing-de` to PyPI and the official MCP registry.

## One-Time Setup Requirements

**PyPI Trusted Publishing:**
PyPI publishing is fully automated via OIDC (no token stored). The Trusted Publisher is configured on PyPI under `cmendezs/mcp-einvoicing-de`, workflow `publish.yml`, environment `pypi`. No `.env` or secret needed.

**MCP Publisher CLI:**
Binary installed at `~/.local/bin/mcp-publisher` (already in `PATH`). To update:
```bash
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_darwin_arm64.tar.gz" \
  | tar xzf - -C ~/.local/bin/
```

**MCP Registry Authentication:**
Authenticate once with GitHub (device flow):
```bash
mcp-publisher login github
```

## Release Steps

**Step 1 — Version bump:** update `version` in `pyproject.toml` and `server.json` (top-level and `packages[].version`).

**Step 2 — Commit, tag and push:**
```bash
git add pyproject.toml server.json
git commit -m "release: v{VERSION} — {summary}"
git push origin main
git tag v{VERSION}
git push origin v{VERSION}
```
GitHub Actions publishes to PyPI automatically on tag push.

**Step 3 — MCP registry:**
```bash
mcp-publisher publish
```

## Changelog

### [0.11.0] - 2026-08-26
#### Fixed
- **[DE-TL-1]** `datev_export._bu_key` mis-mapped two revenue-side categories. Verified against the
  DATEV "Übersicht Steuerschlüssel (BU)" (Dok.-Nr. 1008613, 2026-05-11), the old
  `REVERSE_CHARGE→94` / `INTRA_COMMUNITY→91` are "Erhaltene Leistung §13b" (received/expense)
  codes, wrong for the seller's Ausgangsrechnung side. `_bu_key` is now line_kind-aware: revenue
  `REVERSE_CHARGE→200` (Erbrachte Leistung §13b), `INTRA_COMMUNITY→11` (steuerfreie innergem.
  Lieferung §4 Nr. 1b); expense `→91/94` and `→18/19` by rate; `8`/`9` (Vorsteuer 7/19%) and
  empty-revenue confirmed. All `[Unverified]` BU markers resolved to `[Verified locally]`.
#### Changed
- **[DE-ZF252-3]** Lower-bound pin on `mcp-einvoicing-core` raised to `>=1.21.0` (was `>=1.20.0`),
  picking up the header `ram:TaxTotalAmount` `@currencyID` fix in `EN16931CIISerializer`. Added a
  Saxon-gated regression test asserting the EXTENDED rule `BR-FXEXT-CO-15` does not fire on a
  serialized EXTENDED invoice. The `xslt2` extra pin was raised to `>=1.21.0` accordingly.
#### Notes
- The DATEV Dok. 1008613 PDF used to verify the BU codes is git-ignored (proprietary DATEV
  publication, not redistributed via git or the wheel; see `specs/README.md`).

### [0.10.0] - 2026-08-24
#### Changed
- **[core v1.20.0]** `peppol_send` now emits a real `wsse:Security` message signature. Core's AS4 transport client's `_apply_message_signature` previously computed a signature and discarded it, sending unsigned outbound messages. Wire-level behavior change, not independently validated against a live sandbox Peppol AP at time of publish — the signing code is shared core logic, not DE-specific, so no per-package sandbox gate was required.
- Lower-bound pin on `mcp-einvoicing-core` raised to `>=1.20.0` (was `>=1.19.0`).
- `xslt2` extra now also chains `mcp-einvoicing-core[xslt2]>=1.20.0` alongside the existing direct `saxonche` pin, so both this package's own Factur-X/XRechnung stylesheets and core's new Peppol EUSR/TSR/MLS validators resolve consistently.

#### Added
- Mounted three new opt-in core plugins in `server.py`, alongside the existing Peppol tool plugin: `register_peppol_reporting_tools` (`validate_eusr_report`, `validate_tsr_report`; requires `[xslt2]`), `register_peppol_mls_tools` (`validate_mls_message`, `build_mls_message`; requires `[xslt2]`), and `register_en16931_codelist_tools` (13 `list_*`/`check_*` pairs; requires `EINVOICING_EN16931_CODELIST_DIR`). `peppol_directory_search` arrives automatically via the existing `register_peppol_tools` mount.
- Server-registration smoke test asserting the new tools register.

### [0.9.0] - 2026-08-21
#### Changed
- **[ARCH-CONVERGE-DE]** `server.py` converted from a raw `mcp.server.Server` (low-level protocol handlers, hand-rolled `types.Tool` JSON schemas) to `EInvoicingMCPServer`/`register_plugin`, matching the other country packages. Every `handle_*`/`TOOL_*` pair (`invoice_create`, `invoice_validate`, `invoice_parse`, `invoice_convert`, `datev_export`, `tax_rules`) was converted to a typed FastMCP tool function returning a plain dict, with the removed `TOOL_*` JSON schema descriptions folded into the function docstrings. `peppol_check` and `peppol_send` (DE's own hand-rolled Peppol tools) were removed entirely; `server.py` now mounts `mcp_einvoicing_core.peppol.tools.register_peppol_tools` as a second plugin, with a German-specific identifier adapter (`_de_id_adapter`) that normalizes a bare USt-IdNr to the `9930:<value>` Peppol scheme (`DE:VAT`), verified against the real local OpenPeppol eDEC v9.7 codelist data. DE gains `peppol_get_service_endpoint`, `resolve_peppol_dns`, and 8 eDEC codelist tools it did not have before; `peppol_lookup_participant` replaces `peppol_check` for the existing lookup use case. `peppol_send`'s DE-specific ZUGFeRD-to-XRechnung-UBL conversion step is no longer automatic: compose `invoice_convert` (or `invoice_create` with `target_syntax='UBL'`) with the core `peppol_send` tool instead.
- Lower-bound pin on `mcp-einvoicing-core` raised to `>=1.19.0` (was `>=1.16.1`), required for `register_peppol_tools`.
- Update `audit_vs_core.py`: CHECK 2's tool-registry detection rewritten for plain function names (was raw `types.Tool.name` lookups); CHECK 5's `server.mcp` check now expects an `EInvoicingMCPServer` instance (was `_ALL_TOOLS`/`_TOOL_HANDLERS` dict-sync check); added `resolve_naptr` and `PeppolSMPClient`/`PeppolParticipantId`/`PeppolEnvironment`/`PEPPOL_BIS_BILLING_30` overrides for `mcp_einvoicing_core.peppol` (mounted plugin now imports these, not DE package code directly), plus `compute_retry_delay` (`http_client`) and a second `pdf.Union` override (pre-existing, unrelated gaps surfaced by the core version bump). Audit gate: 0 blocking, 0 warnings.

### [0.8.2] - 2026-08-10
#### Fixed
- **BT-24 Specification Identifier bug (BLOCKING):** `ZUGFeRDProfile.BASIC` emitted the bare `urn:factur-x.eu:1p0:basic` (missing the required `urn:cen.eu:en16931:2017#compliant#` prefix); `ZUGFeRDProfile.EN_16931` emitted `urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931` instead of the correct bare `urn:cen.eu:en16931:2017`. Found by cross-checking against the package's own bundled `specs/examples/zugferd/{BASIC,EN16931}/` and `FACTUR-X_BASIC_codedb.xml` Schematron codelist, both of which already expected the corrected values. `models/zugferd.py`.

#### Changed
- **ZUGFeRD 2.5.2 / Factur-X 1.09.2 spec upgrade** (FeRD/FNFE-MPE release, effective 2026-09-01): replaced bundled `specs/zugferd/{MINIMUM,BASICWL,BASIC,EN16931,EXTENDED}/` schema, Schematron, and XSLT, the runtime copies in `src/mcp_einvoicing_de/rules/`, the example set in `specs/examples/zugferd/`, and `specs/documentation/zugferd/`. Upgraded from ZUGFeRD 2.4 / Factur-X 1.08. The D16B→D22B rebase was a non-issue — `specs/zugferd/XSD_CII_D22B/` was already D22B, byte-identical to the new release. `BR-CO-27`→`CII-SR-470` and the `BR-FXEXT-*` EXTENDED-profile rules were already present in the 1.08 assets. EXTENDED-profile BT-151/BT-151-0 cardinality relaxation only applies to `SubInvoiceLine`/subtype (BT-X-8) `GROUP`/`INFORMATION` lines, which `ZUGFeRDLineItem` does not model — no model change needed.

#### Known issues
- `BR-FXEXT-CO-15` fires on EXTENDED-profile invoices with a VAT total; reproduces under both the old and new bundled stylesheet, so it predates this release. Tracked as DE-ZF252-3 in `roadmap-2026.md`.

### [0.8.0] - 2026-07-20
#### Fixed
- **[DE-SC-1] BLOCKING:** `GermanTaxCategory.REDUCED` emitted invalid EN 16931 category `AA`, causing every reduced-rate (7%) invoice to be rejected by Schematron and by ZRE/OZG-RE. `REDUCED` now aliases the valid category `S`.
- **[DE-SC-2]:** local XRechnung validation ran only the BR-DE CIUS Schematron stylesheet, silently skipping EN 16931 base-rule violations. `_PROFILE_TO_STYLESHEET` now chains base + CIUS per syntax, merging findings across both.
- **[DE-TL-1]:** `datev_export` applied `tax_lines[0].rate` to every line regardless of that line's own tax category/rate, mis-keying reverse-charge lines as exempt. `_bu_key()` + `_resolve_line_tax()` now resolve each line's own tax lines correctly.
- **[DE-TL-2]:** `datev_export` Belegdatum day was not zero-padded, producing a malformed `DDMM`.
- **[DE-TL-3]:** `datev_export`'s per-line branch posted net while the no-line branch posted gross; both now post gross consistently.
- **[DE-LC-1]:** validation was cloud-first by default, sending the full invoice to `validator.kosit.de` without opt-in. Added `cloud_validate: bool = False`.
- **[DE-LC-2]:** the KoSIT cloud endpoint carried an unconditional, unverified default URL. `KoSITValidator` now requires an explicit `base_url`.
- **[DE-LC-3]:** removed `download_rules.py`, which wrote Schematron rules to a directory the loader never read from.
- **[DE-SF-2]:** PDF/A-3 OutputIntent embedded a 128-byte header-only ICC stub, not a valid sRGB profile. Replaced with a real sRGB IEC61966-2.1 profile; added `verapdf.yml` CI conformance check.
- **[DE-SC-3]:** `ZUGFeRDTax`'s tax-amount validator was a dead no-op. Replaced with a real BR-CO-17 `model_validator`.
- **[DE-SF-3]:** Leitweg-ID check-digit validation could false-match a B2B purchase-order reference shaped like a Leitweg-ID and reject a legitimate invoice. Now gated on B2G context (`buyer.leitweg_id` present).
- Audit gate: `CAdESSigner`/`CAdESSignerConfig` (IT/FR-specific CMS signing) were flagged as neither imported nor overridden; added to the intentional-overrides registry. Audit gate now 0 blocking / 0 warnings.
- **[DE-GAP-1]:** bundled FeRD Factur-X Schematron stylesheets were missing their companion `codedb.xml` codelist files, causing Saxon I/O errors on every real-invoice validation. Restored from the vetted `specs/zugferd/` source.
- CI: the new `verapdf.yml` workflow's installer version pin pointed at a nonexistent GitHub Releases asset (veraPDF publishes no GitHub Release assets). Fixed to use the real distribution channel, `software.verapdf.org`.

#### Added
- Bundled DATEV EXTF Buchungsstapel reference specs (`specs/datev/`) with provenance for the `datev_export` tool.

### [0.7.1] - 2026-07-04
#### Changed
- **[DE-XSLT2-1] follow-up:** `validators/schematron.py` no longer carries its own copy of `SaxonSchematronValidator` / XSLT-version detection. Both were promoted into `mcp_einvoicing_core.schematron` in core v1.14.0 (`SaxonSchematronValidator`, `get_xslt_version`, `load_schematron_validator`); the DE `SchematronValidator(stylesheet_key)` factory now resolves the stylesheet path and delegates entirely to core's `load_schematron_validator()`. `SaxonSchematronValidator` is re-exported from this module unchanged so existing imports keep working.
- Bumped the `mcp-einvoicing-core` dependency floor to `>=1.14.0` (was `>=1.12.0`) for the above.
- `tools/invoice_validate.py`'s `_validate_local` now catches `ImportError` alongside `ValueError` around the factory call: core's `SaxonSchematronValidator` raises `ImportError` (not `ValueError`) when the optional `saxonche` extra is missing.

### [0.7.0] - 2026-06-27
#### Added
- **[ARCH-VALID-1d] HIGH:** `ZUGFeRDParty.vat_id` now enforces the DIN 4774 mod-11 check digit on the German USt-IdNr at model construction via a new `@field_validator(mode="after")` delegating to `mcp_einvoicing_core.TaxIdentifier.validate_de_vat` (3-layer party-validation pattern, Layer 1). Validator is scoped to DE-prefixed values so non-DE counterparty VATs (FR, IT, etc.) pass through unchanged for cross-border B2B invoicing. Invalid DE USt-IdNr now raises `ValidationError`.

#### Changed
- Test fixtures rotated from placeholder VATs to mod-11-valid examples (`DE129273398`, `DE136695976`, `DE198765432`) across `tests/conftest.py`, `test_profile_coverage.py`, `test_benchmarks.py`, `test_kosit_canary.py`, and `test_invoice_create.py`. Added `TestZUGFeRDPartyVatIdValidation` covering invalid DE, valid DE, non-DE passthrough, and `None` cases.

### [0.6.0] - 2026-06-25
#### Added
- **DE-SH-2:** PDF/A-3 level B conformance with sRGB ICC profile, OutputIntent, font embedding, and deterministic /ID
- **DE-LC-2:** Cross-syntax CII/UBL conversion via core `convert_wire_format`
- **DE-KOSIT-1:** KoSIT cloud validation default-on with exponential backoff retry (1s/2s/4s) and Schematron fallback
- **DE-PEPPOL-1:** Peppol AS4 outbound transmission via core `PeppolTransmitter`
- **DE-DATEV-1:** DATEV EXTF 700 Buchungsstapel CSV export
- **DE-V1-1:** Full EN 16931 profile coverage verification (6 CII profiles + XRechnung UBL round-trip)
- **DE-V1-2:** KoSIT cloud canary corpus with nightly CI
- **DE-V1-3:** Performance benchmarks (serialize, parse, PDF generate, round-trip)
- **DE-V1-4:** Mutation test configuration (mutmut)

### [0.3.1] - 2026-06-21
#### Fixed
- CI publish workflow: install the `[pdf]` and `[xslt2]` extras alongside `[dev]`
  so the new pikepdf and saxonche-backed tests can actually run; tests skip
  cleanly when the extras are absent locally.

### [0.3.0] - 2026-06-21
#### Added
- **[DE-XSLT2-1] MEDIUM:** `validators/schematron.py` now dispatches to a Saxon-HE
  backend (`SaxonSchematronValidator`) when the optional `[xslt2]` extra is installed.
  All bundled FeRD Factur-X 1.08 and KoSIT XRechnung 3.0.2 stylesheets are XSLT 2.0
  and now execute locally end-to-end. Install with
  `pip install mcp-einvoicing-de[xslt2]`.
- **[DE-B2B-1] MEDIUM:** `invoice_create` enforces the Wachstumschancengesetz
  structured-format mandate for German VAT-registered buyers (DE-prefixed BT-48).
  Non-XML output is rejected unless `transitional_period_opt_in=True` is set.
  Reference: §14 Abs. 2 UStG, BGBl. I Nr. 108.
- **[DE-LC-2] MEDIUM:** `invoice_convert` now implements a real conversion pipeline
  for same-syntax ZUGFeRD profile changes and ZUGFeRD ↔ XRechnung CII swaps with
  data-loss gating. Cross-syntax CII ↔ UBL is structurally rejected pending v0.4.0.
- **[DE-TL-2] MEDIUM:** `tax_rules` Kleinunternehmer entry updated to the
  Jahressteuergesetz 2024 thresholds (€25,000 preceding-year / €100,000 current-year,
  effective 2025-01-01) with verified citation.
- **[DE-TL-3] LOW:** `ZUGFeRDInvoice.tax_representative` (BG-11) field added.
  `ZUGFeRDCIISerializer` emits `ram:SellerTaxRepresentativeTradeParty` after
  `BuyerTradeParty` in the CII tree per HeaderTradeAgreementType sequence.
- **[DE-SH-2] MEDIUM:** `generate_pdf_invoice` now wraps the reportlab output with
  PDF/A-3 XMP identifier metadata (`pdfaid:part="3"`, `pdfaid:conformance="B"`)
  via pikepdf. OutputIntent / sRGB ICC and font embedding remain a follow-up;
  `output_format='pdf'` is documented as experimental and still gated.
- **[DE-LC-3] LOW:** `_extract_xml_from_pdf` implemented via
  `mcp_einvoicing_core.pdf.PDFEmbedder.extract`; tries the canonical Factur-X
  / ZUGFeRD attachment filenames (`factur-x.xml`, `ZUGFeRD-invoice.xml`,
  `zugferd-invoice.xml`, `xrechnung.xml`) in order.
- **[DE-SC-4] LOW:** UBL profile detection XPath verified against the KoSIT
  `validator-configuration-xrechnung v2026-01-31 scenarios.xml`. `[NEED]` marker
  removed; tests added for `XRechnung-UBL` Invoice and CreditNote roots.
#### Removed
- Stale `[NEED:]` markers in `tax_rules.py`, `pdf.py`, `utils/xml_utils.py`,
  and `invoice_validate.py` resolved by the verified replacements above.
#### Notes
- 73 tests passing (20 new). Audit gate PASS (0 blocking, 0 warnings).
- `saxonche` (XSLT 2.0 backend) is opt-in via the `[xslt2]` extra; the wheel
  is large (~40 MB) and shipping it as a hard dependency was rejected.

### [0.2.0] - 2026-06-01
#### Fixed / Added
- **[DE-LC-1] BLOCKING:** `_parse_response` in `validators/kosit.py` rewritten for the
  actual KoSIT validationtool v1.5+ REST JSON shape (`violations[]` with `type`/`context`/
  `test`/`text`). `Accept: application/json` added. Fail-safe for absent `valid` and
  unrecognised response shape.
- **[DE-SC-2] BLOCKING:** `_PROFILE_TO_STYLESHEET` wired to profile-specific FeRD
  Schematron keys; prevents full EN 16931 ruleset from producing false positives on
  MINIMUM and BASIC-WL profiles.
- **[DE-SH-3] MEDIUM:** 8 Schematron XSLT files (FeRD 1.08 + KoSIT XRechnung
  3.0.2/2026-01-31) bundled in the wheel via hatchling package-data auto-discovery.
- **[DE-TL-1] MEDIUM:** `utils/leitweg.py` with ISO 7064 MOD 97-10 check-digit validator
  and format regex. Applied strictly to `ZUGFeRDParty.leitweg_id`; pattern-guarded on
  `XRechnungInvoice.buyer_reference`.
- **[DE-XSLT2-1]** FeRD Schematron XSLTs use XPath 2.0; lxml (XSLT 1.0) cannot compile
  them. `ValueError` caught gracefully with `STYLESHEET-XSLT2-INCOMPATIBLE` structured
  error directing users to `use_remote_kosit=True`.
- 51 tests passing; audit gate PASS (0 blocking).

### [0.1.4] - 2026-06-01
#### Fixed
- **[DE-SC-1] BLOCKING:** `ZUGFeRDProfile.XRECHNUNG` URN corrected from stale
  `urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.3` to
  `urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0` (verified
  against KoSIT `scenarios.xml` from release `v2026-01-31`).
- **[DE-SH-1] MEDIUM:** `etree.fromstring` replaced with `safe_fromstring` from core
  in `detect_zugferd_profile`. Eliminates XXE vector on inbound XML inspection.
- **[DE-SC-3] MEDIUM:** `XRechnungInvoice.buyer_reference` overridden as `str = Field(...)`
  (mandatory). Enforces BR-DE-15 at Pydantic construction time.
- `specs/README.md`: XRechnung URN domain corrected (`xeinkauf.de`, not `xoev-de`).
- 29 tests passing; audit gate PASS (0 blocking).

### [0.1.3] - 2026-05-31
#### Added
- **[DE-CORE-1]** `mcp_einvoicing_de/serializers.py` with four classes extending
  `mcp-einvoicing-core` v1.3.0 wire formats: `ZUGFeRDCIISerializer`,
  `ZUGFeRDCIIParser`, `XRechnungUBLSerializer`, `XRechnungUBLParser`.
- `invoice_create` tool now live: routes to CII (ZUGFeRD) or UBL (XRechnung) syntax.
  Replaces the `{"error": "XML generation not yet implemented"}` stub.
- `invoice_parse` tool now live: `ZUGFeRDCIIParser` and `XRechnungUBLParser` replace
  the `_parse_cii_xml` / `_parse_ubl_xml` stubs.
- **[DE-SF-1]** `specs/` created with ZUGFeRD 1.08 + KoSIT XRechnung 3.0.2/2026-01-31
  artefacts, CII D22B XSD, UBL 2.1 schemas, and `specs/README.md`.

---

## Notes

- The MCP registry does **not** sync automatically with PyPI or GitHub — step 3 is required for every release.
- The `server.json` description field must be **≤ 100 characters**.
- PyPI rejects re-uploads of the same version — always bump before tagging.
