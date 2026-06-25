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
