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
    transitional_period_opt_in: bool = Field(
        False,
        description=(
            "Acknowledge the Wachstumschancengesetz transitional period (2025-2026) "
            "and explicitly permit non-XML output for a German VAT-registered buyer. "
            "Set to True only when the buyer has agreed in writing to receive PDF or "
            "another non-structured format. From 2027 the transitional grace ends for "
            "large businesses; from 2028 all B2B invoices to German VAT-registered "
            "buyers must be in a structured EN 16931 format. Source: §14 Abs. 2 UStG, "
            "Wachstumschancengesetz of 27 March 2024 (BGBl. I Nr. 108)."
        ),
    )


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
        "When the buyer is a German VAT-registered business (DE-prefixed VAT id), the "
        "Wachstumschancengesetz B2B mandate (effective 2025-01-01, §14 Abs. 2 UStG) "
        "requires a structured EN 16931 invoice. Non-XML output is rejected unless "
        "transitional_period_opt_in is set to True (allowed only 2025-2026 with the "
        "buyer's written consent)."
    ),
    inputSchema={
        "type": "object",
        "required": ["invoice"],
        "properties": {
            "invoice": {"type": "object", "description": "Invoice data (ZUGFeRDInvoice schema)"},
            "output_format": {"type": "string", "enum": ["xml", "pdf"], "default": "xml"},
            "syntax": {"type": "string", "enum": ["CII", "UBL"], "default": "CII"},
            "pretty_print": {"type": "boolean", "default": True},
            "transitional_period_opt_in": {"type": "boolean", "default": False},
        },
    },
)


_DE_B2B_MANDATE_NOTE = (
    "Germany E-Rechnungsgesetz / Wachstumschancengesetz (effective 2025-01-01) requires "
    "a structured EN 16931 invoice (ZUGFeRD 2.x or XRechnung) for B2B transactions where "
    "the buyer is registered for German VAT (DE-prefixed UStIdNr). Reference: §14 Abs. 2 "
    "UStG, as amended by the Wachstumschancengesetz of 27 March 2024 (BGBl. I Nr. 108). "
    "Transitional rules: 2025-2026 PDF or other non-structured formats are permitted with "
    "the buyer's consent; 2027 the grace period ends for issuers with turnover above "
    "EUR 800,000; from 2028 structured EN 16931 output is mandatory for all B2B issuers. "
    "Set transitional_period_opt_in=True to acknowledge the transition rules and emit a "
    "non-XML format during the 2025-2026 window."
)


def _buyer_requires_de_b2b_mandate(buyer_vat_id: str | None) -> bool:
    """Return True when the buyer is registered for German VAT (BT-48 starts with DE)."""
    if not buyer_vat_id:
        return False
    return buyer_vat_id.strip().upper().startswith("DE")


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

    # B2B mandate check — reject non-XML output for German VAT-registered buyers unless
    # the caller explicitly opts in to the 2025-2026 transitional period.
    if (
        params.output_format != "xml"
        and _buyer_requires_de_b2b_mandate(invoice.buyer.vat_id)
        and not params.transitional_period_opt_in
    ):
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": (
                            "DE B2B mandate: a structured EN 16931 invoice is required for a "
                            "German VAT-registered buyer. Use output_format='xml', or set "
                            "transitional_period_opt_in=True after confirming the buyer's "
                            "written consent to receive a non-structured format under the "
                            "Wachstumschancengesetz 2025-2026 transitional rules."
                        ),
                        "mandate_note": _DE_B2B_MANDATE_NOTE,
                        "buyer_vat_id": invoice.buyer.vat_id,
                    }
                ),
            )
        ]

    if params.output_format == "pdf":
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": (
                            "PDF (ZUGFeRD hybrid) output is gated as experimental and is not "
                            "yet emitted by invoice_create. The current generate_pdf_invoice "
                            "applies PDF/A-3 XMP metadata (pdfaid:part=3, pdfaid:conformance=B) "
                            "but does not yet embed an OutputIntent / sRGB ICC profile or "
                            "embed fonts, which ISO 19005-3 level B requires. Tracked as "
                            "DE-SH-2 follow-up."
                        ),
                        "hint": (
                            "Use output_format='xml' for now. For an interim hybrid PDF, "
                            "generate the XML here and pass it together with a "
                            "separately-produced PDF/A-3 conformant carrier through "
                            "mcp_einvoicing_de.utils.pdf.embed_xml_in_pdf."
                        ),
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
