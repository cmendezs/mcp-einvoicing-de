"""MCP tool: invoice_parse — extract structured data from ZUGFeRD / XRechnung files.

Accepts:
- Raw CII or UBL XML
- Base64-encoded XML
- Base64-encoded PDF (ZUGFeRD hybrid — extracts embedded XML attachment)

Returns a structured JSON representation matching the ZUGFeRDInvoice schema.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import mcp.types as types
from mcp_einvoicing_core.base_server import scrub
from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.xml_utils import format_error, resolve_xml_input
from pydantic import BaseModel, Field

from mcp_einvoicing_de.serializers import XRechnungUBLParser, ZUGFeRDCIIParser
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


_ZUGFERD_ATTACHMENT_FILENAMES: tuple[str, ...] = (
    # Factur-X / ZUGFeRD 2.x — current Factur-X 1.0+ default
    "factur-x.xml",
    # ZUGFeRD 1.x legacy filename, still encountered in older hybrid PDFs
    "ZUGFeRD-invoice.xml",
    "zugferd-invoice.xml",
    # XRechnung hybrid (when distributed inside a PDF/A-3 envelope)
    "xrechnung.xml",
)


def _extract_xml_from_pdf(pdf_bytes: bytes) -> bytes:
    """Extract the ZUGFeRD / Factur-X XML attachment from a PDF/A-3 file.

    Delegates to mcp_einvoicing_core.pdf.PDFEmbedder.extract. Tries the well-known
    Factur-X / ZUGFeRD attachment filenames in order. Returns the XML bytes of the
    first match.

    The filename order follows FeRD ZUGFeRD 2.x §3.4 (factur-x.xml is canonical
    for Factur-X 1.0+; ZUGFeRD-invoice.xml is the ZUGFeRD 1.x legacy name).

    Raises:
        EInvoicingError: If no known ZUGFeRD attachment is present in the PDF.
        ImportError:     If pikepdf is not installed
                         (install with `pip install mcp-einvoicing-de[pdf]`).
    """
    from mcp_einvoicing_core.exceptions import EInvoicingError
    from mcp_einvoicing_core.pdf import PDFEmbedder

    for filename in _ZUGFERD_ATTACHMENT_FILENAMES:
        xml_bytes = PDFEmbedder.extract(pdf_bytes, filename=filename)
        if xml_bytes:
            logger.debug("Extracted ZUGFeRD attachment %r (%d bytes)", filename, len(xml_bytes))
            return xml_bytes

    raise EInvoicingError(
        "No ZUGFeRD / Factur-X XML attachment found in the PDF. "
        f"Looked for: {', '.join(_ZUGFERD_ATTACHMENT_FILENAMES)}."
    )


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
        except (ValueError, TypeError) as exc:
            return [types.TextContent(type="text", text=json.dumps(format_error(f"Invalid base64 PDF input: {exc}")))]
        try:
            xml_bytes = _extract_xml_from_pdf(pdf_bytes)
        except ImportError as exc:
            return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]
        except EInvoicingError as exc:
            return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]
        except Exception as exc:
            return [types.TextContent(type="text", text=json.dumps(format_error(f"PDF extraction failed: {exc}")))]
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

    try:
        if syntax.value == "CII":
            invoice = ZUGFeRDCIIParser().parse(xml_bytes)
        else:
            invoice = XRechnungUBLParser().parse(xml_bytes)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    invoice_data = scrub(invoice.model_dump(mode="json"))
    raw_xml = xml_bytes.decode("utf-8", errors="replace") if params.include_raw_xml else None
    output = InvoiceParseOutput(
        profile=profile.name if profile else (invoice.profile.name if hasattr(invoice.profile, "name") else str(invoice.profile)),
        syntax=syntax.value,
        invoice_number=invoice.invoice_number,
        invoice_date=str(invoice.invoice_date),
        seller_name=invoice.seller.name if invoice.seller else None,
        buyer_name=invoice.buyer.name if invoice.buyer else None,
        tax_inclusive_amount=str(invoice.tax_inclusive_amount),
        currency_code=invoice.currency_code,
        invoice_data=invoice_data,
        raw_xml=scrub(raw_xml) if raw_xml is not None else None,
    )

    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
