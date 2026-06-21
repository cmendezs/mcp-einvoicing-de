"""PDF/A-3 generation and ZUGFeRD XML embedding utilities for mcp-einvoicing-de.

generate_pdf_invoice() produces a human-readable PDF from a ZUGFeRDInvoice and
applies the minimal PDF/A-3 metadata wrapping (XMP pdfaid:part/pdfaid:conformance)
through pikepdf when it is installed. embed_xml_in_pdf() attaches the ZUGFeRD XML
to the PDF using the core PDFEmbedder.

PDF/A-3 conformance status of the output of generate_pdf_invoice (DE-SH-2):

- Applied: XMP pdfaid:part="3", pdfaid:conformance="B"; /AF and embedded file via
  PDFEmbedder.embed downstream.
- Not yet applied: OutputIntent with embedded sRGB ICC profile, full font
  embedding (reportlab Standard 14 fonts are not embedded by default), and a
  deterministic trailer /ID. Full ISO 19005-3 level B conformance therefore is
  not yet reached and the `output_format='pdf'` path in invoice_create remains
  gated. Tracked as a follow-up to DE-SH-2.

The AFRelationship for the ZUGFeRD XML attachment is "Alternative" per FeRD
Factur-X 1.08 §6.1; the embedded XML filename is "factur-x.xml" per the same
section. The Factur-X XMP ConformanceLevel string is the profile name with a
space replacing the underscore (e.g. "EN 16931", "BASIC WL"), per FeRD
Factur-X 1.08 §6.2.2.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice

logger = logging.getLogger(__name__)

# Map ZUGFeRDProfile enum names → Factur-X XMP ConformanceLevel string
# (FeRD Factur-X 1.08 §6.2.2 table).
_PROFILE_CONFORMANCE: dict[str, str] = {
    "MINIMUM":   "MINIMUM",
    "BASIC_WL":  "BASIC WL",
    "BASIC":     "BASIC",
    "EN_16931":  "EN 16931",
    "EXTENDED":  "EXTENDED",
    "XRECHNUNG": "XRECHNUNG",
}


def _apply_pdfa3_metadata(pdf_bytes: bytes) -> bytes:
    """Attach the minimal PDF/A-3 XMP identifier metadata to *pdf_bytes*.

    Adds pdfaid:part="3" and pdfaid:conformance="B" to the document XMP stream
    so downstream consumers (and the core PDFEmbedder) see the file as targeting
    PDF/A-3. Does not embed an OutputIntent / ICC profile and does not embed
    fonts; full ISO 19005-3 conformance requires both, see module docstring.

    When pikepdf is not installed the original bytes are returned unchanged and
    a warning is logged.
    """
    try:
        import pikepdf
        from pikepdf import Name
    except ImportError:
        logger.warning(
            "pikepdf is not installed; skipping PDF/A-3 metadata wrapping. "
            "Install with `pip install mcp-einvoicing-de[pdf]` for a closer-to-conformant PDF."
        )
        return pdf_bytes

    pdfa_block = (
        '    <rdf:Description rdf:about=""\n'
        '        xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">\n'
        '      <pdfaid:part>3</pdfaid:part>\n'
        '      <pdfaid:conformance>B</pdfaid:conformance>\n'
        '    </rdf:Description>'
    )

    src = BytesIO(pdf_bytes)
    dst = BytesIO()
    with pikepdf.open(src) as pdf:
        existing_xmp: bytes = b""
        if "/Metadata" in pdf.Root:
            try:
                existing_xmp = bytes(pdf.Root["/Metadata"].read_bytes())
            except Exception:
                existing_xmp = b""

        xmp_str = existing_xmp.decode("utf-8", errors="replace")
        close_tag = "</rdf:RDF>"
        if close_tag in xmp_str:
            xmp_str = xmp_str.replace(close_tag, f"{pdfa_block}\n  {close_tag}", 1)
        else:
            xmp_str = (
                '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
                '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
                '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
                f"{pdfa_block}\n"
                "  </rdf:RDF>\n"
                "</x:xmpmeta>\n"
                '<?xpacket end="w"?>'
            )

        xmp_stream = pdf.make_stream(xmp_str.encode("utf-8"))
        xmp_stream["/Type"] = Name("/Metadata")
        xmp_stream["/Subtype"] = Name("/XML")
        pdf.Root["/Metadata"] = xmp_stream

        pdf.save(dst)
    return dst.getvalue()


def generate_pdf_invoice(invoice: ZUGFeRDInvoice) -> bytes:
    """Generate a human-readable PDF invoice and apply PDF/A-3 XMP metadata.

    Returns raw PDF bytes. The output carries pdfaid:part="3" /
    pdfaid:conformance="B" XMP fields when pikepdf is available, which is the
    minimum metadata layer required for the Factur-X hybrid envelope. The
    output is still missing OutputIntent / ICC and embedded fonts; see the
    module docstring for the remaining DE-SH-2 follow-up.

    The text layout is intentionally minimal for v0.3.0: invoice number,
    invoice date, and tax-inclusive amount. The full sender / recipient /
    line-item / VAT-breakdown layout is tracked separately.
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
    return _apply_pdfa3_metadata(buffer.getvalue())


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
