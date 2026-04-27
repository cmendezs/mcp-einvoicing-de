"""PDF/A-3 generation and ZUGFeRD XML embedding utilities.

ZUGFeRD requires attaching the XML invoice to a PDF/A-3 file with a specific
attachment relationship. This module provides helpers for both generating
a human-readable PDF invoice and embedding the XML into an existing PDF.

PDF/A-3 conformance requirements:
- ISO 19005-3 (PDF/A-3)
- Attachment relationship: 'Alternative' (for ZUGFeRD) or 'Source' (for XRechnung)
- AFRelationship key in file spec dictionary

[NEED: confirm ZUGFeRD 2.3 required AFRelationship value — 'Alternative' vs 'Data']
[NEED: confirm whether mcp-einvoicing-core provides a PDF/A-3 embedding utility]
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice

logger = logging.getLogger(__name__)


def generate_pdf_invoice(invoice: "ZUGFeRDInvoice") -> bytes:
    """
    Generate a human-readable PDF invoice using reportlab.

    Returns raw PDF bytes (not yet PDF/A-3 conformant).
    Call :func:`embed_xml_in_pdf` afterwards to attach the XML and
    set PDF/A-3 metadata.

    [NEED: implement full PDF layout matching typical German invoice format]
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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
    # - Sender block (top-right)
    # - Recipient block
    # - Invoice header (number, date, due date)
    # - Line items table
    # - Tax breakdown table
    # - Total amounts
    # - Payment instructions
    # - Footer with legal notices

    story.append(Paragraph(f"Rechnung {invoice.invoice_number}", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Rechnungsdatum: {invoice.invoice_date.strftime('%d.%m.%Y')}", styles["Normal"]
        )
    )
    story.append(
        Paragraph(f"Gesamtbetrag: {invoice.tax_inclusive_amount} {invoice.currency_code}", styles["Normal"])
    )

    doc.build(story)
    return buffer.getvalue()


def embed_xml_in_pdf(pdf_bytes: bytes, xml_bytes: bytes, profile_name: str = "EN 16931") -> bytes:
    """
    Embed *xml_bytes* into *pdf_bytes* as a PDF/A-3 attachment.

    The XML is attached with filename 'factur-x.xml' and AFRelationship
    set per ZUGFeRD 2.3 specification.

    [NEED: implement PDF/A-3 conformant embedding]
    [NEED: determine correct AFRelationship for each ZUGFeRD profile]
    [NEED: evaluate PyMuPDF vs pikepdf for PDF/A-3 conformance]
    """
    # TODO: implement PDF/A-3 embedding
    # Option A: PyMuPDF (fitz) — requires pymupdf extra
    # Option B: pikepdf — pure Python, simpler PDF/A metadata handling
    # Option C: reportlab + manual xref injection
    raise NotImplementedError(
        "PDF/A-3 XML embedding is not yet implemented. "
        "Tracked in roadmap v0.2.0. "
        "[NEED: choose and implement PDF/A-3 embedding library]"
    )
