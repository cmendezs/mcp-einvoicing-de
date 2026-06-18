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
