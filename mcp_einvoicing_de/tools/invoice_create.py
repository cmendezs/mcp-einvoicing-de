"""MCP tool: invoice_create — generate ZUGFeRD or XRechnung invoices.

Produces:
- CII XML for ZUGFeRD (all profiles) and XRechnung CII
- UBL XML for XRechnung UBL
- PDF/A-3 hybrid (ZUGFeRD) when output_format='pdf' (roadmap v0.2.0)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types
from pydantic import BaseModel, Field

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice
from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile
from mcp_einvoicing_de.serializers import XRechnungUBLSerializer, ZUGFeRDCIISerializer

logger = logging.getLogger(__name__)


class InvoiceCreateInput(BaseModel):
    """Input schema for invoice_create."""

    invoice: dict[str, Any] = Field(
        ...,
        description=(
            "Invoice data matching the ZUGFeRDInvoice schema. "
            "Set invoice.profile to XRECHNUNG to produce an XRechnung invoice. "
            "See tool description for field reference."
        ),
    )
    output_format: str = Field(
        "xml",
        description="Output format: 'xml' (default) or 'pdf' (ZUGFeRD hybrid PDF/A-3, roadmap v0.2.0).",
    )
    syntax: str = Field(
        "CII",
        description="XML syntax: 'CII' (default) or 'UBL' (XRechnung only).",
    )
    pretty_print: bool = Field(True, description="Pretty-print the XML output.")


class InvoiceCreateOutput(BaseModel):
    """Output schema for invoice_create."""

    xml_content: str | None = Field(None, description="Generated XML string (output_format='xml')")
    pdf_base64: str | None = Field(
        None, description="Base64-encoded PDF bytes (output_format='pdf')"
    )
    profile: str
    syntax: str
    invoice_number: str


TOOL_INVOICE_CREATE = types.Tool(
    name="invoice_create",
    description=(
        "Generate a ZUGFeRD 2.x or XRechnung 3.x invoice in XML (CII or UBL) format. "
        "Supports all ZUGFeRD profiles: MINIMUM, BASIC_WL, BASIC, EN_16931, EXTENDED. "
        "For XRechnung, set profile to XRECHNUNG and choose CII or UBL syntax. "
        "PDF/A-3 hybrid output is planned for v0.2.0."
    ),
    inputSchema={
        "type": "object",
        "required": ["invoice"],
        "properties": {
            "invoice": {"type": "object", "description": "Invoice data (ZUGFeRDInvoice schema)"},
            "output_format": {"type": "string", "enum": ["xml", "pdf"], "default": "xml"},
            "syntax": {"type": "string", "enum": ["CII", "UBL"], "default": "CII"},
            "pretty_print": {"type": "boolean", "default": True},
        },
    },
)


async def handle_invoice_create(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for invoice_create."""
    try:
        params = InvoiceCreateInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    try:
        profile_str = params.invoice.get("profile", "EN_16931")
        if profile_str == ZUGFeRDProfile.XRECHNUNG.name or profile_str == ZUGFeRDProfile.XRECHNUNG.value:
            invoice = XRechnungInvoice.model_validate(
                {**params.invoice, "syntax": params.syntax}
            )
        else:
            invoice = ZUGFeRDInvoice.model_validate(params.invoice)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Invoice validation failed: {exc}"}))]

    if params.output_format == "pdf":
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "PDF output is not yet implemented (planned for v0.2.0).",
                        "hint": "Use output_format='xml' and embed manually with invoice_convert.",
                    }
                ),
            )
        ]

    try:
        if params.syntax == "UBL":
            if not isinstance(invoice, XRechnungInvoice):
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": "UBL syntax is only supported for XRechnung invoices."}
                        ),
                    )
                ]
            xml_bytes = XRechnungUBLSerializer().serialize(invoice, pretty_print=params.pretty_print)
        else:
            xml_bytes = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=params.pretty_print)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Serialization failed: {exc}"}))]

    output = InvoiceCreateOutput(
        xml_content=xml_bytes.decode("utf-8"),
        profile=invoice.profile.name,
        syntax=params.syntax,
        invoice_number=invoice.invoice_number,
    )
    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
