"""Utility helpers for XML processing, PDF generation, and ID validation."""

from mcp_einvoicing_de.utils.leitweg import looks_like_leitweg_id, validate_leitweg_id
from mcp_einvoicing_de.utils.pdf import embed_xml_in_pdf, generate_pdf_invoice
from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile

__all__ = [
    "detect_invoice_syntax",
    "detect_zugferd_profile",
    "generate_pdf_invoice",
    "embed_xml_in_pdf",
    "validate_leitweg_id",
    "looks_like_leitweg_id",
]
