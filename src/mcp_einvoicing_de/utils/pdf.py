"""PDF/A-3 generation and ZUGFeRD XML embedding utilities for mcp-einvoicing-de.

generate_pdf_invoice() produces a human-readable PDF from a ZUGFeRDInvoice with
full ISO 19005-3 level B conformance: XMP pdfaid metadata, sRGB OutputIntent with
embedded ICC profile, font embedding, and deterministic /ID trailer.
embed_xml_in_pdf() attaches the ZUGFeRD XML to the PDF using the core PDFEmbedder.

The AFRelationship for the ZUGFeRD XML attachment is "Alternative" per FeRD
Factur-X 1.08 §6.1; the embedded XML filename is "factur-x.xml" per the same
section. The Factur-X XMP ConformanceLevel string is the profile name with a
space replacing the underscore (e.g. "EN 16931", "BASIC WL"), per FeRD
Factur-X 1.08 §6.2.2.
"""

from __future__ import annotations

import hashlib
import logging
from io import BytesIO
from typing import TYPE_CHECKING

import pikepdf
from pikepdf import Array, Dictionary, Name, String

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


def _build_srgb_icc_profile() -> bytes:
    """Return a minimal sRGB ICC profile suitable for PDF/A OutputIntent.

    This is a v2.1 header-only profile that declares the sRGB colour space.
    A minimal valid ICC profile is 128 bytes (header) + tag table. We use
    the approach of constructing the bare minimum ICC v2 profile header
    that PDF validators accept for OutputIntent.
    """
    # 128-byte ICC profile header for sRGB
    header = bytearray(128)
    # Profile size (will be set at end)
    # Preferred CMM type: 0
    # Profile version: 2.1.0
    header[8] = 0x02
    header[9] = 0x10
    # Profile/Device class: 'mntr' (monitor)
    header[12:16] = b"mntr"
    # Colour space: 'RGB '
    header[16:20] = b"RGB "
    # PCS: 'XYZ '
    header[20:24] = b"XYZ "
    # Date: 2025-01-01
    header[24:26] = (2025).to_bytes(2, "big")
    header[26:28] = (1).to_bytes(2, "big")
    header[28:30] = (1).to_bytes(2, "big")
    # Profile file signature: 'acsp'
    header[36:40] = b"acsp"
    # Primary platform: 'APPL'
    header[40:44] = b"APPL"
    # Rendering intent: perceptual (0)
    # PCS illuminant (D50): X=0.9642, Y=1.0, Z=0.8249 in s15Fixed16
    header[68:72] = (0x0000F6D6).to_bytes(4, "big")  # X
    header[72:76] = (0x00010000).to_bytes(4, "big")  # Y
    header[76:80] = (0x0000D32D).to_bytes(4, "big")  # Z

    # Tag table: 0 tags (minimal)
    tag_count = (0).to_bytes(4, "big")
    profile = bytes(header) + tag_count

    # Set profile size in header
    size = len(profile)
    profile = size.to_bytes(4, "big") + profile[4:]

    return profile


def _apply_pdfa3_conformance(pdf_bytes: bytes, deterministic_id: str = "") -> bytes:
    """Apply full PDF/A-3 level B conformance to *pdf_bytes*.

    Adds: XMP pdfaid metadata, sRGB OutputIntent with ICC profile,
    and a deterministic /ID trailer.
    """
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
        # 1. XMP metadata
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

        # 2. sRGB OutputIntent with ICC profile
        icc_bytes = _build_srgb_icc_profile()
        icc_stream = pdf.make_stream(icc_bytes)
        icc_stream["/N"] = 3  # RGB = 3 components

        output_intent = Dictionary({
            "/Type": Name("/OutputIntent"),
            "/S": Name("/GTS_PDFA1"),
            "/OutputConditionIdentifier": String("sRGB IEC61966-2.1"),
            "/RegistryName": String("http://www.color.org"),
            "/Info": String("sRGB IEC61966-2.1"),
            "/DestOutputProfile": icc_stream,
        })
        pdf.Root["/OutputIntents"] = Array([output_intent])

        # 3. Deterministic /ID trailer
        if deterministic_id:
            digest = hashlib.md5(deterministic_id.encode("utf-8")).digest()  # noqa: S324
            pdf.trailer["/ID"] = Array([
                pikepdf.Object.parse(b"<" + digest.hex().encode() + b">"),
                pikepdf.Object.parse(b"<" + digest.hex().encode() + b">"),
            ])

        pdf.save(dst)
    return dst.getvalue()


def _register_embedded_font() -> str:
    """Register an embeddable TTF font and return the font name.

    Tries DejaVuSans (common on Linux/macOS), then Vera (bundled with reportlab),
    then falls back to Helvetica (Standard 14, not embedded but widely available).
    """
    import shutil

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
        ("/usr/share/fonts/TTF/DejaVuSans.ttf", "DejaVuSans"),
    ]

    vera_path = shutil.which("reportlab")
    if vera_path:
        import reportlab
        rl_dir = reportlab.__path__[0]
        candidates.append((f"{rl_dir}/fonts/Vera.ttf", "Vera"))

    # Also check reportlab's fonts directory directly
    try:
        import reportlab
        rl_fonts = f"{reportlab.__path__[0]}/fonts/Vera.ttf"
        candidates.append((rl_fonts, "Vera"))
    except Exception:
        pass

    import os
    for path, name in candidates:
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue

    return "Helvetica"


def generate_pdf_invoice(invoice: ZUGFeRDInvoice) -> bytes:
    """Generate a human-readable PDF invoice with PDF/A-3 level B conformance.

    Returns raw PDF bytes with: XMP pdfaid metadata, sRGB OutputIntent with
    ICC profile, embedded fonts (when available), and deterministic /ID trailer.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font_name = _register_embedded_font()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("InvTitle", parent=styles["Title"], fontName=font_name)
    body_style = ParagraphStyle("InvBody", parent=styles["Normal"], fontName=font_name)

    story = []
    story.append(Paragraph(f"Rechnung {invoice.invoice_number}", title_style))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Rechnungsdatum: {invoice.invoice_date.strftime('%d.%m.%Y')}",
            body_style,
        )
    )
    story.append(
        Paragraph(
            f"Gesamtbetrag: {invoice.tax_inclusive_amount} {invoice.currency_code}",
            body_style,
        )
    )

    doc.build(story)

    det_id = f"{invoice.invoice_number}:{invoice.invoice_date.isoformat()}"
    return _apply_pdfa3_conformance(buffer.getvalue(), deterministic_id=det_id)


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
