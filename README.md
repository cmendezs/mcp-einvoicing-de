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
└── Tools: create / validate / parse / convert / peppol_check / peppol_send / datev_export / tax_rules

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
| `[xslt2]` | Saxon-HE backend for XSLT 2.0 Schematron stylesheets (FeRD Factur-X 1.08 and KoSIT XRechnung 3.0.2). Required for local Schematron validation; lxml supports XSLT 1.0 only. | `pip install mcp-einvoicing-de[xslt2]` |
| `[pdf]` | Additional PDF utilities for embedded XML extraction (`pikepdf` is also a base dependency for PDF/A-3 generation). | `pip install mcp-einvoicing-de[pdf]` |
| `[pymupdf]` | Alternative PDF engine (uses `PyMuPDF`). | `pip install mcp-einvoicing-de[pymupdf]` |
| `[dev]` | Development tools (pytest, ruff, pre-commit). | `pip install mcp-einvoicing-de[dev]` |

---

## ⚙️ Configuration

The server does not require external credentials. Available environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EINVOICING_DE_LOG_LEVEL` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `EINVOICING_DE_KOSIT_VALIDATOR_URL` | URL of a self-hosted KoSIT validation tool REST endpoint (overrides the default `https://validator.kosit.de`) | |
| `EINVOICING_DE_KOSIT_DISABLE` | Set to `1` to disable KoSIT cloud validation entirely (local Schematron only) | |
| `EINVOICING_DE_PEPPOL_CERT_PATH` | Path to the X.509 certificate for Peppol AS4 signing (PEM or DER) | |
| `EINVOICING_DE_PEPPOL_KEY_PATH` | Path to the private key for Peppol AS4 signing (PEM or DER) | |
| `EINVOICING_DE_PEPPOL_KEY_PASSWORD` | Password for the private key (if encrypted) | |

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
| `invoice_validate` | Validate an invoice against EN 16931 and KoSIT rules (BR-DE-\*). KoSIT cloud validation (`validator.kosit.de`) is enabled by default with exponential backoff retry (1s/2s/4s) and automatic Schematron fallback. Disable with `EINVOICING_DE_KOSIT_DISABLE=1`. XSLT 2.0 local validation requires the `[xslt2]` extra. |
| `invoice_parse` | Extract structured data from ZUGFeRD or XRechnung XML, or from a PDF/A-3 hybrid invoice with embedded `factur-x.xml` / `zugferd-invoice.xml`. |
| `invoice_convert` | Convert between ZUGFeRD profiles, swap ZUGFeRD/XRechnung CII headers, or perform cross-syntax CII/UBL conversion via core `convert_wire_format`. |
| `peppol_check` | Check Peppol participant registration of a German company via SMP/SML lookup. |
| `peppol_send` | Send an invoice to a Peppol recipient via AS4 outbound transmission. Converts ZUGFeRD to XRechnung UBL (Peppol BIS 3.0 profile), signs with X.509 credentials, and returns the AS4 receipt. Requires `EINVOICING_DE_PEPPOL_CERT_PATH` and `EINVOICING_DE_PEPPOL_KEY_PATH`. |
| `datev_export` | Export a ZUGFeRD invoice as a DATEV EXTF 700 Buchungsstapel CSV file for import into DATEV accounting software. Defaults to SKR 03 accounts (8400 revenue / 10000 receivable). |
| `tax_rules` | Query German VAT rules (rates, §13b UStG reverse charge codes, §19 UStG Kleinunternehmer thresholds at JStG 2024 values of €25,000 preceding year / €100,000 current year, exemptions). |

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
3. peppol_check(
     participant_id="0204:991-1234512345-06",
     environment="production"
   )
   → {
       "is_registered": true,
       "participant_id": "0204:991-1234512345-06",
       "document_type_supported": true,
       "access_point_url": "https://ap.example.de/as4",
       "transport_profile": "peppol-transport-as4-v2.0"
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
| ZUGFeRD | 2.3.2 | MINIMUM, BASIC WL, BASIC, EN 16931, EXTENDED |
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

Current version: **v0.6.0**.

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
| 🇪🇸 Spain | [mcp-facturacion-electronica-es](https://github.com/cmendezs/mcp-facturacion-electronica-es) |

---

## 📄 License

This project is licensed under the **Apache 2.0 License**.  
See the [LICENSE](LICENSE) file for details.

Copyright 2026 cmendezs

---

*Project maintained by [cmendezs](https://github.com/cmendezs). For questions about the ZUGFeRD or XRechnung specification implementation, please open an issue.*
