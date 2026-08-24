"""MCP server entrypoint for mcp-einvoicing-de."""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp_einvoicing_core import EInvoicingMCPServer
from mcp_einvoicing_core.en16931_codelist_tools import register_en16931_codelist_tools
from mcp_einvoicing_core.peppol.mls_tools import register_peppol_mls_tools
from mcp_einvoicing_core.peppol.reporting_tools import register_peppol_reporting_tools
from mcp_einvoicing_core.peppol.tools import register_peppol_tools

from mcp_einvoicing_de.tools.datev_export import datev_export
from mcp_einvoicing_de.tools.invoice_convert import invoice_convert
from mcp_einvoicing_de.tools.invoice_create import invoice_create
from mcp_einvoicing_de.tools.invoice_parse import invoice_parse
from mcp_einvoicing_de.tools.invoice_validate import invoice_validate
from mcp_einvoicing_de.tools.tax_rules import tax_rules

LOG_LEVEL = os.environ.get("EINVOICING_DE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


def _de_id_adapter(identifier: str) -> str:
    """Normalize a bare German VAT ID (USt-IdNr) to a Peppol participant ID.

    Scheme 9930 (DE:VAT, "Germany VAT number") per the OpenPeppol eDEC
    Participant Identifier Schemes code list. Already scheme-qualified
    identifiers (containing ':') pass through unchanged.
    """
    if ":" in identifier:
        return identifier
    cleaned = identifier.strip().upper()
    if not cleaned.startswith("DE"):
        cleaned = f"DE{cleaned}"
    return f"9930:{cleaned}"


def _register_de_tools(mcp: Any) -> None:
    """Register all German e-invoicing tools onto the shared FastMCP instance."""
    mcp.tool()(invoice_create)
    mcp.tool()(invoice_validate)
    mcp.tool()(invoice_parse)
    mcp.tool()(invoice_convert)
    mcp.tool()(datev_export)
    mcp.tool()(tax_rules)


mcp = EInvoicingMCPServer(
    "mcp-einvoicing-de",
    instructions=(
        "MCP server for German electronic invoicing: ZUGFeRD 2.x and XRechnung 3.x "
        "generation, validation, parsing, conversion, DATEV export, and German VAT "
        "rules lookup. peppol_lookup_participant and related Peppol network tools "
        "accept a bare German VAT ID (normalized to Peppol scheme 9930) or a full "
        "participant ID."
    ),
)
mcp.register_plugin(_register_de_tools, "de")
mcp.register_plugin(lambda m: register_peppol_tools(m, id_adapter=_de_id_adapter), "peppol")
mcp.register_plugin(register_peppol_reporting_tools, "peppol-reporting")
mcp.register_plugin(register_peppol_mls_tools, "peppol-mls")
mcp.register_plugin(register_en16931_codelist_tools, "en16931-codelists")


def main() -> None:
    """CLI entrypoint registered in pyproject.toml."""
    mcp.run()


if __name__ == "__main__":
    main()
