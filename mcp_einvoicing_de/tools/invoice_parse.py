"""MCP tool: invoice_parse — extract structured data from ZUGFeRD / XRechnung files.

Accepts:
- Raw CII or UBL XML
- Base64-encoded XML
- Base64-encoded PDF (ZUGFeRD hybrid — extracts embedded XML attachment)

Returns a structured JSON representation matching the ZUGFeRDInvoice schema.

[NEED: verify if mcp-einvoicing-core provides a base CII/UBL parser to extend]
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import mcp.types as types
from pydantic import BaseModel, Field

from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.xml_utils import format_error, resolve_xml_input
from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile

logger = logging.getLogger(__name__)


class InvoiceParseInput(BaseModel):
    """Input schema for invoice_parse."""

    xml_content: str | None = Field(None, description="Raw XML string.")
    xml_base64: str | None = Field(None, description="Base64-encoded XML bytes.")
    pdf_base64: str | None = Field(
        None,
        description=(
            "Base64-encoded PDF bytes. The tool will extract the embedded XML "
            "attachment (ZUGFeRD hybrid PDF/A-3)."
        ),
    )
    include_raw_xml: bool = Field(
        False, description="Include the raw XML string in the response."
    )


class InvoiceParseOutput(BaseModel):
    """Output schema for invoice_parse."""

    profile: str
    syntax: str
    invoice_number: str | None = None
    invoice_date: str | None = None
    seller_name: str | None = None
    buyer_name: str | None = None
    tax_inclusive_amount: str | None = None
    currency_code: str | None = None
    invoice_data: dict[str, Any] = Field(
        default_factory=dict, description="Full parsed invoice matching ZUGFeRDInvoice schema."
    )
    raw_xml: str | None = None


TOOL_INVOICE_PARSE = types.Tool(
    name="invoice_parse",
    description=(
        "Extract structured data from a ZUGFeRD 2.x or XRechnung 3.x invoice. "
        "Accepts raw XML (CII or UBL), base64-encoded XML, or base64-encoded PDF "
        "(ZUGFeRD hybrid — the XML is extracted from the PDF/A-3 attachment). "
        "Returns a structured JSON object matching the invoice data model."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "xml_content": {"type": "string", "description": "Raw XML string."},
            "xml_base64": {"type": "string", "description": "Base64-encoded XML."},
            "pdf_base64": {"type": "string", "description": "Base64-encoded PDF (ZUGFeRD hybrid)."},
            "include_raw_xml": {"type": "boolean", "default": False},
        },
        "anyOf": [
            {"required": ["xml_content"]},
            {"required": ["xml_base64"]},
            {"required": ["pdf_base64"]},
        ],
    },
)


def _extract_xml_from_pdf(pdf_bytes: bytes) -> bytes:
    """
    Extract the ZUGFeRD XML attachment from a PDF/A-3 file.

    [NEED: implement PDF attachment extraction]
    [NEED: confirm attachment filename — 'factur-x.xml' or 'ZUGFeRD-invoice.xml']
    [NEED: verify if mcp-einvoicing-core provides a PDF extraction utility]
    """
    # TODO: implement using PyMuPDF (fitz) or pikepdf
    # fitz approach:
    #   import fitz
    #   doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    #   for i in range(doc.embfile_count()):
    #       info = doc.embfile_info(i)
    #       if info['filename'] in ('factur-x.xml', 'ZUGFeRD-invoice.xml', 'xrechnung.xml'):
    #           return doc.embfile_get(i)
    raise NotImplementedError(
        "PDF extraction not yet implemented. "
        "Provide xml_content or xml_base64 directly. "
        "[NEED: implement PDF/A-3 attachment extraction]"
    )


def _parse_cii_xml(xml_bytes: bytes) -> dict[str, Any]:
    """
    Parse CII XML into a dict matching ZUGFeRDInvoice schema.

    [NEED: implement full CII XPath extraction]
    [NEED: verify if mcp-einvoicing-core provides a CII deserialiser]
    """
    # TODO: implement CII parsing
    # Key XPaths (abbreviated):
    # - Invoice number:  //rsm:ExchangedDocument/ram:ID
    # - Invoice date:    //rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString
    # - Seller name:     //ram:SellerTradeParty/ram:Name
    # - Buyer name:      //ram:BuyerTradeParty/ram:Name
    # - Total with VAT:  //ram:GrandTotalAmount
    # [NEED: full namespace map and XPath list for all EN 16931 BT-* elements in CII]
    return {"_TODO": "CII parser not implemented"}


def _parse_ubl_xml(xml_bytes: bytes) -> dict[str, Any]:
    """
    Parse UBL XML into a dict matching ZUGFeRDInvoice schema.

    [NEED: implement full UBL XPath extraction]
    [NEED: verify if mcp-einvoicing-core provides a UBL deserialiser]
    """
    # TODO: implement UBL parsing
    return {"_TODO": "UBL parser not implemented"}


async def handle_invoice_parse(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for invoice_parse."""
    try:
        params = InvoiceParseInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    # Resolve input to XML bytes
    xml_bytes: bytes
    if params.pdf_base64 is not None:
        try:
            pdf_bytes = base64.b64decode(params.pdf_base64)
            xml_bytes = _extract_xml_from_pdf(pdf_bytes)
        except (NotImplementedError, EInvoicingError, Exception) as exc:
            return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]
    else:
        try:
            xml_bytes = resolve_xml_input(params.xml_content, params.xml_base64)
        except (ValueError, EInvoicingError) as exc:
            return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        syntax = detect_invoice_syntax(xml_bytes)
        profile = detect_zugferd_profile(xml_bytes)
    except ValueError as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    if syntax == "CII" or syntax.value == "CII":
        invoice_data = _parse_cii_xml(xml_bytes)
    else:
        invoice_data = _parse_ubl_xml(xml_bytes)

    output = InvoiceParseOutput(
        profile=profile.name if profile else "UNKNOWN",
        syntax=syntax.value if hasattr(syntax, "value") else str(syntax),
        invoice_data=invoice_data,
        raw_xml=xml_bytes.decode("utf-8", errors="replace") if params.include_raw_xml else None,
    )

    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
