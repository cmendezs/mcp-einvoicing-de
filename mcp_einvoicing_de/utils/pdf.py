"""PDF/A-3 generation and ZUGFeRD XML embedding utilities for mcp-einvoicing-de.

generate_pdf_invoice() produces a human-readable PDF from a ZUGFeRDInvoice.
embed_xml_in_pdf() attaches the ZUGFeRD XML to the PDF using the core
PDFEmbedder (requires pikepdf).

The AFRelationship for ZUGFeRD 2.x is "Alternative".
[Unverified: confirm the correct value for ZUGFeRD 2.3 and for XRechnung hybrid]

The Factur-X XMP ConformanceLevel is derived from the invoice profile name.
[Unverified: confirm exact string values expected by FeRD / ZUGFeRD validators]
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice

logger = logging.getLogger(__name__)

# Map ZUGFeRDProfile enum names → XMP ConformanceLevel strings
# [Unverified: confirm ConformanceLevel values from FeRD ZUGFeRD 2.3 spec]
_PROFILE_CONFORMANCE: dict[str, str] = {
    "MINIMUM":   "MINIMUM",
    "BASIC_WL":  "BASIC WL",
    "BASIC":     "BASIC",
    "EN_16931":  "EN 16931",
    "EXTENDED":  "EXTENDED",
    "XRECHNUNG": "XRECHNUNG",
}


def generate_pdf_invoice(invoice: ZUGFeRDInvoice) -> bytes:
    """Generate a human-readable PDF invoice using reportlab.

    Returns raw PDF bytes (not yet PDF/A-3 conformant — use embed_xml_in_pdf
    afterwards to attach the ZUGFeRD XML and update the PDF/A-3 metadata).

    [NEED: implement full invoice layout (sender/recipient blocks, line items
     table, tax breakdown, payment instructions, footer with legal notices)]
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF generation. "
            "Install it with: pip install reportlab"
        ) from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    # TODO: implement full invoice layout
    story.append(Paragraph(f"Rechnung {invoice.invoice_number}", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Rechnungsdatum: {invoice.invoice_date.strftime('%d.%m.%Y')}",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"Gesamtbetrag: {invoice.tax_inclusive_amount} {invoice.currency_code}",
            styles["Normal"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def embed_xml_in_pdf(
    pdf_bytes: bytes,
    xml_bytes: bytes,
    profile_name: str = "EN_16931",
) -> bytes:
    """Embed ZUGFeRD XML into a PDF as a PDF/A-3 named attachment.

    Delegates to mcp_einvoicing_core.pdf.PDFEmbedder.  Requires pikepdf
    (install with: pip install pikepdf  or  pip install mcp-einvoicing-de[pdf]).

    Args:
        pdf_bytes:    Source PDF bytes (from generate_pdf_invoice or any PDF).
        xml_bytes:    ZUGFeRD CII XML bytes to attach.
        profile_name: ZUGFeRDProfile enum name (e.g. "EN_16931", "XRECHNUNG").
                      Used to set the Factur-X XMP ConformanceLevel.

    Returns:
        PDF/A-3 bytes with the XML attachment and updated XMP metadata.
    """
    from mcp_einvoicing_core.pdf import PDFEmbedder

    xmp_profile = _PROFILE_CONFORMANCE.get(profile_name.upper(), profile_name)

    return PDFEmbedder.embed(
        pdf_bytes=pdf_bytes,
        xml_bytes=xml_bytes,
        filename="factur-x.xml",
        afrelationship="Alternative",
        xmp_profile=xmp_profile,
    )
