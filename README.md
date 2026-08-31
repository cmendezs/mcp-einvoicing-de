# mcp-einvoicing-de 🇩🇪

[English](README.md) | [Deutsch](README.de.md)

<!-- mcp-name: io.github.cmendezs/mcp-einvoicing-de -->

![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
[![PyPI version](https://img.shields.io/pypi/v/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![mcp-einvoicing-de MCP server](https://glama.ai/mcp/servers/cmendezs/mcp-einvoicing-de/badges/score.svg)](https://glama.ai/mcp/servers/cmendezs/mcp-einvoicing-de)

MCP server (Model Context Protocol) in Python for **German electronic invoicing** in **ZUGFeRD 2.x** and **XRechnung 3.x** formats (EN 16931, FeRD, KoSIT). Enables AI agents (Claude, IDEs) to create, validate, parse, and convert e-invoices that are fully compliant with the German B2B e-invoicing mandate (effective from 2025, phased enforcement through 2027 to 2028) and the European standard EN 16931.

---

## 🏗️ Built on

This package is built on [**mcp-einvoicing-core**](https://github.com/cmendezs/mcp-einvoicing-core), a shared base library for European e-invoicing MCP servers. It provides shared models, validation abstractions, XML utilities, and the exception hierarchy.

`mcp-einvoicing-core` is automatically installed as a transitive dependency, no additional step required.

> **For developers:** `pip install -e ".[dev]"` installs the base package automatically from PyPI.

---

## 🏗️ Architecture

```
mcp-einvoicing-de (this package, standalone MCP server)
├── ZUGFeRDInvoice / XRechnungInvoice  ← Pydantic models (all profiles)
├── SchematronValidator                ← EN 16931 + KoSIT BR-DE-* rules
├── KoSITValidator                     ← Remote validation tool (optional)
└── Tools: create / validate / parse / convert / datev_export / tax_rules
    (+ core Peppol tool plugin, mounted separately: lookup / send / DNS / codelists)

        ↑ extends
mcp-einvoicing-core (shared base, installed as dependency)
├── BaseDocumentGenerator / Validator / Parser
├── BaseInvoice, BaseParty … (Pydantic)
├── xml_utils, exceptions
└── EInvoicingMCPServer
```

---

## 🚀 Installation

### Via PyPI (recommended)

```bash
pip install mcp-einvoicing-de
```

Without prior installation, using `uvx`:

```bash
uvx mcp-einvoicing-de
```

### From source

```bash
git clone https://github.com/cmendezs/mcp-einvoicing-de.git
cd mcp-einvoicing-de

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

### Optional extras

| Extra | Purpose | Install |
|-------|---------|---------|
| `[xslt2]` | Saxon-HE backend for XSLT 2.0 Schematron stylesheets (FeRD Factur-X 1.09.2 and KoSIT XRechnung 3.0.2). Required for local Schematron validation; lxml supports XSLT 1.0 only. | `pip install mcp-einvoicing-de[xslt2]` |
| `[pdf]` | Additional PDF utilities for embedded XML extraction (`pikepdf` is also a base dependency for PDF/A-3 generation). | `pip install mcp-einvoicing-de[pdf]` |
| `[pymupdf]` | Alternative PDF engine (uses `PyMuPDF`). | `pip install mcp-einvoicing-de[pymupdf]` |
| `[dev]` | Development tools (pytest, ruff, pre-commit). | `pip install mcp-einvoicing-de[dev]` |

---

## ⚙️ Configuration

The server does not require external credentials. Available environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EINVOICING_DE_LOG_LEVEL` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `EINVOICING_DE_KOSIT_VALIDATOR_URL` | URL of a self-hosted KoSIT validation tool REST endpoint. Only used if cloud validation is enabled — see `EINVOICING_DE_KOSIT_ENABLE` | |
| `EINVOICING_DE_KOSIT_ENABLE` | Set to `1` to enable KoSIT cloud validation (`validator.kosit.de` or a self-hosted endpoint). Local Schematron-only validation is the default | |
| `EINVOICING_PEPPOL_CODELIST_DIR` | Local directory containing your own copy of the OpenPeppol eDEC Code Lists, required by the Peppol codelist tools (not bundled with this package; see `mcp-einvoicing-core` README) | |
| `EINVOICING_EN16931_CODELIST_DIR` | Local directory containing your own copy of the CEF "Digital Building Blocks" EN 16931 semantic code lists, required by the EN 16931 codelist tools (not bundled; see `mcp-einvoicing-core` README) | |

The EUSR/TSR reporting and MLS tools additionally require the `[xslt2]` extra for Schematron validation.

### 🤖 Claude Desktop integration

Add the following entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "uvx",
      "args": ["mcp-einvoicing-de"]
    }
  }
}
```

### ⌨️ Cursor integration

Configuration file (`~/.cursor/mcp.json` or `.cursor/mcp.json` in the project directory):

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "uvx",
      "args": ["mcp-einvoicing-de"]
    }
  }
}
```

### 🪐 Kiro integration

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "uvx",
      "args": ["mcp-einvoicing-de"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

---

## 🧰 Available MCP tools

| Tool | Description |
|------|-------------|
| `invoice_create` | Generate ZUGFeRD or XRechnung XML (CII or UBL). Enforces the §14 Abs. 2 UStG B2B mandate: non-XML output is rejected for DE-prefixed VAT buyers unless `transitional_period_opt_in=True` is set. `output_format='pdf'` produces a PDF/A-3 level B hybrid invoice with sRGB ICC profile, OutputIntent, embedded fonts, and deterministic /ID. |
| `invoice_validate` | Validate an invoice against EN 16931 and KoSIT rules (BR-DE-\*). Local Schematron validation runs by default (no data leaves your machine); set `cloud_validate=True` or `EINVOICING_DE_KOSIT_ENABLE=1` to opt into KoSIT cloud validation (`validator.kosit.de` or a self-hosted endpoint) with exponential backoff retry (1s/2s/4s). XSLT 2.0 local validation requires the `[xslt2]` extra. |
| `invoice_parse` | Extract structured data from ZUGFeRD or XRechnung XML, or from a PDF/A-3 hybrid invoice with embedded `factur-x.xml` / `zugferd-invoice.xml`. |
| `invoice_convert` | Convert between ZUGFeRD profiles, swap ZUGFeRD/XRechnung CII headers, or perform cross-syntax CII/UBL conversion via core `convert_wire_format`. |
| `datev_export` | Export a ZUGFeRD invoice as a DATEV EXTF 700 Buchungsstapel CSV file for import into DATEV accounting software. Defaults to SKR 03 accounts (8400 revenue / 10000 receivable). |
| `tax_rules` | Query German VAT rules (rates, §13b UStG reverse charge codes, §19 UStG Kleinunternehmer thresholds at JStG 2024 values of €25,000 preceding year / €100,000 current year, exemptions). |

### Peppol network tools

Peppol participant lookup, service-endpoint lookup, a DNS-only diagnostic, AS4 send, Peppol Directory search, and the OpenPeppol eDEC codelist tools are provided by the shared core Peppol tool plugin (`mcp_einvoicing_core.peppol.tools.register_peppol_tools`), mounted in `server.py` with a German-specific identifier adapter: a bare USt-IdNr (e.g. `123456789` or `DE123456789`) is normalized to the `9930:<value>` Peppol scheme (`DE:VAT`); an already scheme-qualified identifier (e.g. `9930:DE123456789`, or `0204:<leitweg-id>` for Leitweg-ID-routed B2G invoices) passes through unchanged. To send via AS4, first produce XRechnung UBL with `invoice_convert` (or `invoice_create` with `target_syntax='UBL'`), then pass the result to `peppol_send`.

`peppol_send` signs outbound messages with a real `wsse:Security` signature as of `mcp-einvoicing-core` v1.20.0 (previously computed and discarded — see CHANGELOG.md v0.10.0).

| Tool | Description |
|---|---|
| `peppol_lookup_participant` | Check whether a business is registered on the Peppol network; returns registration status and supported document types |
| `peppol_get_service_endpoint` | Fetch the AS4 endpoint for a participant's document type |
| `resolve_peppol_dns` | DNS-only (SML) diagnostic, independent of SMP reachability |
| `peppol_send` | Transmit a UBL/CII invoice via AS4 |
| `peppol_directory_search` | Search the public Peppol Directory by participant, name, country, or document type |
| `list_participant_id_schemes`, `list_document_type_ids`, `list_process_ids`, `list_spis_use_case_ids` | OpenPeppol eDEC codelist lookups (require `EINVOICING_PEPPOL_CODELIST_DIR`) |
| `check_document_type_id_in_codelist`, `check_process_id_in_codelist`, `check_participant_id_scheme_in_codelist`, `get_peppol_codelist_version` | OpenPeppol eDEC codelist checks and version reporting |

See the [`mcp-einvoicing-core` README](https://github.com/cmendezs/mcp-einvoicing-core#readme) for full parameter documentation on these tools.

---

### Peppol reporting and status tools

Added in v0.10.0 via three opt-in core plugins, mounted unconditionally in `server.py`. Each raises a clear error at call time (not at registration) if its extra or data directory is missing.

| Tool | Plugin | Description |
|---|---|---|
| `validate_eusr_report` | `register_peppol_reporting_tools` | Validate an End User Statistics Report (XSD, then Schematron). Requires the `[xslt2]` extra. |
| `validate_tsr_report` | `register_peppol_reporting_tools` | Validate a Transaction Statistics Report (XSD, then Schematron). Requires the `[xslt2]` extra. |
| `validate_mls_message` | `register_peppol_mls_tools` | Validate a Message Level Status document (UBL `ApplicationResponse-2` subset). Requires the `[xslt2]` extra. |
| `build_mls_message` | `register_peppol_mls_tools` | Build a document-level MLS response. Requires the `[xslt2]` extra. |
| 13 `list_*`/`check_*` pairs, `get_en16931_codelist_version` | `register_en16931_codelist_tools` | EN 16931 semantic code list lookups/checks (units, VAT categories, etc.). Require `EINVOICING_EN16931_CODELIST_DIR`. |

See the [`mcp-einvoicing-core` README](https://github.com/cmendezs/mcp-einvoicing-core#readme) for full parameter documentation on these tools.

---

## Usage examples

### Example 1: Validate an invoice

```
1. invoice_validate(
     xml_base64="...",   # Base64-encoded ZUGFeRD XML
     strict=True
   )
   → {
       "is_valid": true,
       "profile": "EN_16931",
       "syntax": "CII",
       "error_count": 0,
       "warning_count": 2,
       "errors": [],
       "warnings": [...],
       "validator_used": "local_schematron"
     }
```

### Example 2: Query German tax rules

```
2. tax_rules(query="reverse_charge", context="Bauleistungen")
   → {
       "results": [
         {
           "paragraph": "§13b Abs. 2 Nr. 5 UStG",
           "description_en": "Construction services (building contractor rule)",
           "vatex_code": "VATEX-EU-AE",
           "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)"
         }
       ],
       "legal_disclaimer": "..."
     }
```

### Example 3: Check Peppol registration

```
3. peppol_lookup_participant(
     identifier="123456789",   # bare USt-IdNr, normalized to 9930:DE123456789
     environment="production"
   )
   → {
       "is_registered": true,
       "participant_id": "9930:DE123456789",
       "supported_document_types": ["urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"],
       "smp_hostname": "b-...iso6523-actorid-upis.edelivery.tech.ec.europa.eu"
     }
```

### Example 4: Parse invoice data

```
4. invoice_parse(xml_base64="...", include_raw_xml=False)
   → {
       "profile": "XRECHNUNG",
       "syntax": "CII",
       "invoice_number": "RE-2025-001",
       "invoice_date": "2025-01-15",
       "seller_name": "Muster GmbH",
       "buyer_name": "Käufer AG",
       "tax_inclusive_amount": "119.00",
       "currency_code": "EUR"
     }
```

---

## 📚 Supported standards

| Standard | Version | Profiles / Syntax |
|----------|---------|-------------------|
| ZUGFeRD | 2.5.2 | MINIMUM, BASIC WL, BASIC, EN 16931, EXTENDED |
| XRechnung | 3.0.2 | CII (Cross Industry Invoice), UBL (Universal Business Language) |
| EN 16931 | 2017 | European core data model for electronic invoicing |
| Peppol BIS | 3.0 | Billing 3.0 (EN 16931-compliant) |

> **Note:** ZUGFeRD 2.x and XRechnung 3.x share the same CII XML syntax at the EN 16931 profile level. Conversion between both formats is therefore possible without data loss. The EXTENDED profile is specific to ZUGFeRD and has no XRechnung equivalent.

| Resource | Link |
|----------|------|
| FeRD ZUGFeRD specification | [ferd-net.de](https://www.ferd-net.de) |
| KoSIT XRechnung | [xeinkauf.de](https://xeinkauf.de/xrechnung/) |
| KoSIT validation tool | [github.com/itplr-kosit/validationtool](https://github.com/itplr-kosit/validationtool) |
| EN 16931-1:2017 | [CEN](https://www.cen.eu/) |
| Peppol BIS Billing 3.0 | [docs.peppol.eu](https://docs.peppol.eu/poacc/billing/3.0/) |

---

## 🧪 Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest tests/ -v

# With coverage report
pytest --cov=mcp_einvoicing_de --cov-report=term-missing

# Model tests only
pytest tests/test_models.py -v
```

---

## Roadmap

Current version: **v0.8.0**.

For the history of past releases, see [RELEASE.md](RELEASE.md).

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

```bash
git clone https://github.com/cmendezs/mcp-einvoicing-de.git
cd mcp-einvoicing-de
pip install -e ".[dev]"
pytest
make audit
```

---

## Other e-invoicing MCP servers

| Country | Server |
|---------|--------|
| 🌍 Global | [mcp-einvoicing-core](https://github.com/cmendezs/mcp-einvoicing-core) |
| 🇧🇪 Belgium | [mcp-einvoicing-be](https://github.com/cmendezs/mcp-einvoicing-be) |
| 🇧🇷 Brazil | [mcp-nfe-br](https://github.com/cmendezs/mcp-nfe-br) |
| 🇫🇷 France | [mcp-facture-electronique-fr](https://github.com/cmendezs/mcp-facture-electronique-fr) |
| 🇩🇪 Germany | [mcp-einvoicing-de](https://github.com/cmendezs/mcp-einvoicing-de) |
| 🇮🇹 Italy | [mcp-fattura-elettronica-it](https://github.com/cmendezs/mcp-fattura-elettronica-it) |
| 🇵🇱 Poland | [mcp-ksef-pl](https://github.com/cmendezs/mcp-ksef-pl) |
| 🇸🇬 Singapore | [mcp-invoicenow-sg](https://github.com/cmendezs/mcp-invoicenow-sg) |
| 🇪🇸 Spain | [mcp-facturacion-electronica-es](https://github.com/cmendezs/mcp-facturacion-electronica-es) |
| 🇦🇪 United Arab Emirates | [mcp-einvoicing-ae](https://github.com/cmendezs/mcp-einvoicing-ae) |

---

## 📄 License

This project is licensed under the **Apache 2.0 License**.  
See the [LICENSE](LICENSE) file for details.

Copyright 2026 cmendezs

---

*Project maintained by [cmendezs](https://github.com/cmendezs). For questions about the ZUGFeRD or XRechnung specification implementation, please open an issue.*
