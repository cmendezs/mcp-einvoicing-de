# mcp-einvoicing-de

[![PyPI version](https://img.shields.io/pypi/v/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/pypi/pyversions/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![CI](https://github.com/cmendezs/mcp-einvoicing-de/actions/workflows/publish.yml/badge.svg)](https://github.com/cmendezs/mcp-einvoicing-de/actions/workflows/publish.yml)

**`mcp-einvoicing-de` is a Python MCP (Model Context Protocol) server for German electronic invoicing.** It enables AI assistants and LLM-powered applications to create, validate, parse, and convert ZUGFeRD 2.x and XRechnung 3.x invoices in full compliance with the German B2B e-invoicing mandate (effective 2025, phased enforcement through 2027–2028) and the European standard EN 16931. The package is designed for developers, tax software vendors, and ERP integrators who need to expose e-invoicing capabilities to AI agents. It is part of the **mcp-einvoicing ecosystem** — a family of country-specific MCP servers built on the shared `mcp-einvoicing-core` library.

---

## Installation

```bash
pip install mcp-einvoicing-de
```

For development:

```bash
pip install "mcp-einvoicing-de[dev]"
```

### MCP Client Configuration

Add the server to your MCP client configuration (e.g., Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "mcp-einvoicing-de"
    }
  }
}
```

---

## Quick Start

```python
# Run as a standalone MCP server (stdio transport)
mcp-einvoicing-de

# Or programmatically
from mcp_einvoicing_de.server import main
import asyncio
asyncio.run(main())
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `invoice_create` | Generate a ZUGFeRD or XRechnung invoice (XML or PDF/A-3) |
| `invoice_validate` | Validate an invoice against EN 16931 and KoSIT Schematron rules |
| `invoice_parse` | Extract structured data from an existing ZUGFeRD or XRechnung file |
| `invoice_convert` | Convert between ZUGFeRD profiles or between ZUGFeRD and XRechnung |
| `peppol_check` | Verify a German company's Peppol participant registration (AS4) |
| `tax_rules` | Query German VAT rules (Steuerklassen, reverse charge, §13b UStG) |

---

## Configuration

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `EINVOICING_DE_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `EINVOICING_DE_KOSIT_VALIDATOR_URL` | — | Override KoSIT validator endpoint (optional) |
| `EINVOICING_DE_PEPPOL_SMP_URL` | — | Override Peppol SMP lookup URL (optional) |
| `EINVOICING_DE_PDF_ENGINE` | `reportlab` | PDF generation engine (`reportlab` or `pymupdf`) |

---

## Standards Supported

| Standard | Version | Profiles / Syntax |
|----------|---------|-------------------|
| ZUGFeRD | 2.3 | MINIMUM, BASIC WL, BASIC, EN 16931, EXTENDED |
| XRechnung | 3.x | CII (Cross Industry Invoice), UBL (Universal Business Language) |
| EN 16931 | — | European core invoice semantic model |
| Peppol BIS | 3.0 | Billing 3.0 (DE PINT) |

> **Note**: ZUGFeRD 2.x and XRechnung 3.x share the same CII XML syntax at the EN 16931 profile level, making conversion straightforward. The EXTENDED profile is ZUGFeRD-specific and has no XRechnung equivalent.

---

## Roadmap

- [ ] v0.1.0 — Core tools: create, validate, parse, convert, peppol_check, tax_rules
- [ ] v0.2.0 — PDF/A-3 embedding (ZUGFeRD hybrid) via `reportlab` / `PyMuPDF`
- [ ] v0.3.0 — Full KoSIT online validator integration
- [ ] v0.4.0 — Peppol AS4 direct submission support
- [ ] v0.5.0 — DATEV export format support
- [ ] v1.0.0 — Production-ready, full EN 16931 coverage

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

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Related Projects

- [`mcp-einvoicing-core`](https://github.com/cmendezs/mcp-einvoicing-core) — Shared library
- [`mcp-facture-electronique-fr`](https://github.com/cmendezs/mcp-facture-electronique-fr) — French e-invoicing MCP server
