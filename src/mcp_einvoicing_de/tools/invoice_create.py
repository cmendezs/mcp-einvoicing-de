"""MCP tool: invoice_create — generate ZUGFeRD or XRechnung invoices.

Produces:
- CII XML for ZUGFeRD (all profiles) and XRechnung CII
- UBL XML for XRechnung UBL
- PDF/A-3 hybrid (ZUGFeRD) when output_format='pdf' (roadmap v0.2.0)
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_einvoicing_core.xml_utils import format_error
from pydantic import BaseModel, Field

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice
from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile
from mcp_einvoicing_de.serializers import XRechnungUBLSerializer, ZUGFeRDCIISerializer

logger = logging.getLogger(__name__)


class InvoiceCreateOutput(BaseModel):
    """Output schema for invoice_create."""

    xml_content: str | None = Field(None, description="Generated XML string (output_format='xml')")
    pdf_base64: str | None = Field(
        None, description="Base64-encoded PDF bytes (output_format='pdf')"
    )
    profile: str
    syntax: str
    invoice_number: str


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


async def invoice_create(
    invoice: dict[str, Any],
    output_format: str = "xml",
    syntax: str = "CII",
    pretty_print: bool = True,
    transitional_period_opt_in: bool = False,
) -> dict[str, Any]:
    """Generate a ZUGFeRD 2.x or XRechnung 3.x invoice in XML (CII or UBL) format.

    Supports all ZUGFeRD profiles: MINIMUM, BASIC_WL, BASIC, EN_16931, EXTENDED.
    For XRechnung, set profile to XRECHNUNG and choose CII or UBL syntax.
    When the buyer is a German VAT-registered business (DE-prefixed VAT id), the
    Wachstumschancengesetz B2B mandate (effective 2025-01-01, §14 Abs. 2 UStG)
    requires a structured EN 16931 invoice. Non-XML output is rejected unless
    transitional_period_opt_in is set to True (allowed only 2025-2026 with the
    buyer's written consent).

    Args:
        invoice: Invoice data matching the ZUGFeRDInvoice schema. Set
            invoice.profile to XRECHNUNG to produce an XRechnung invoice.
        output_format: 'xml' (default) or 'pdf' (ZUGFeRD hybrid PDF/A-3).
        syntax: XML syntax: 'CII' (default) or 'UBL' (XRechnung only).
        pretty_print: Pretty-print the XML output.
        transitional_period_opt_in: Acknowledge the Wachstumschancengesetz
            transitional period (2025-2026) and explicitly permit non-XML
            output for a German VAT-registered buyer. Set to True only when
            the buyer has agreed in writing to receive PDF or another
            non-structured format. From 2027 the transitional grace ends for
            large businesses; from 2028 all B2B invoices to German
            VAT-registered buyers must be in a structured EN 16931 format.
            Source: §14 Abs. 2 UStG, Wachstumschancengesetz of 27 March 2024
            (BGBl. I Nr. 108).
    """
    try:
        profile_str = invoice.get("profile", "EN_16931")
        if profile_str == ZUGFeRDProfile.XRECHNUNG.name or profile_str == ZUGFeRDProfile.XRECHNUNG.value:
            invoice_model = XRechnungInvoice.model_validate({**invoice, "syntax": syntax})
        else:
            invoice_model = ZUGFeRDInvoice.model_validate(invoice)
    except Exception as exc:
        return {"error": f"Invoice validation failed: {exc}"}

    # B2B mandate check: reject non-XML output for German VAT-registered buyers unless
    # the caller explicitly opts in to the 2025-2026 transitional period.
    if (
        output_format != "xml"
        and _buyer_requires_de_b2b_mandate(invoice_model.buyer.vat_id)
        and not transitional_period_opt_in
    ):
        return {
            "error": (
                "DE B2B mandate: a structured EN 16931 invoice is required for a "
                "German VAT-registered buyer. Use output_format='xml', or set "
                "transitional_period_opt_in=True after confirming the buyer's "
                "written consent to receive a non-structured format under the "
                "Wachstumschancengesetz 2025-2026 transitional rules."
            ),
            "mandate_note": _DE_B2B_MANDATE_NOTE,
            "buyer_vat_id": invoice_model.buyer.vat_id,
        }

    if output_format == "pdf":
        try:
            import pikepdf  # noqa: F401
        except ImportError:
            return format_error(
                "pikepdf is required for PDF output. Install it with: pip install pikepdf"
            )

    try:
        if syntax == "UBL":
            if not isinstance(invoice_model, XRechnungInvoice):
                return {"error": "UBL syntax is only supported for XRechnung invoices."}
            xml_bytes = XRechnungUBLSerializer().serialize(invoice_model, pretty_print=pretty_print)
        else:
            xml_bytes = ZUGFeRDCIISerializer().serialize(invoice_model, pretty_print=pretty_print)
    except Exception as exc:
        return {"error": f"Serialization failed: {exc}"}

    if output_format == "pdf":
        import base64

        from mcp_einvoicing_de.utils.pdf import embed_xml_in_pdf, generate_pdf_invoice

        try:
            pdf_bytes = generate_pdf_invoice(invoice_model)
            pdf_bytes = embed_xml_in_pdf(pdf_bytes, xml_bytes, invoice_model.profile.name)
        except Exception as exc:
            return format_error(f"PDF generation failed: {exc}")

        output = InvoiceCreateOutput(
            pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
            profile=invoice_model.profile.name,
            syntax=syntax,
            invoice_number=invoice_model.invoice_number,
        )
        return output.model_dump()

    output = InvoiceCreateOutput(
        xml_content=xml_bytes.decode("utf-8"),
        profile=invoice_model.profile.name,
        syntax=syntax,
        invoice_number=invoice_model.invoice_number,
    )
    return output.model_dump()
