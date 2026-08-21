"""Tests for the PDF generation and extraction helpers."""

from __future__ import annotations

import base64
import importlib.util

import pytest

from mcp_einvoicing_de.tools.invoice_parse import _extract_xml_from_pdf
from mcp_einvoicing_de.utils.pdf import generate_pdf_invoice

_PIKEPDF_AVAILABLE = importlib.util.find_spec("pikepdf") is not None
_pikepdf_required = pytest.mark.skipif(
    not _PIKEPDF_AVAILABLE,
    reason="pikepdf extra not installed (install with mcp-einvoicing-de[pdf])",
)


class TestGeneratePdfInvoice:
    @_pikepdf_required
    def test_pdf_carries_pdfaid_xmp_metadata(self, minimal_invoice) -> None:
        pdf_bytes = generate_pdf_invoice(minimal_invoice)
        # The minimal PDF/A-3 metadata block is injected as XMP and stays in the
        # uncompressed body of the output PDF.
        assert b"%PDF-" in pdf_bytes[:10]
        assert b"pdfaid:part" in pdf_bytes
        assert b"pdfaid:conformance" in pdf_bytes

    def test_pdf_generation_succeeds_without_pikepdf(self, minimal_invoice) -> None:
        # Even without the pikepdf extra, the reportlab base PDF is returned;
        # the wrapping helper is a no-op and logs a warning.
        pdf_bytes = generate_pdf_invoice(minimal_invoice)
        assert b"%PDF-" in pdf_bytes[:10]


@_pikepdf_required
class TestExtractXmlFromPdf:
    def test_round_trip_via_pdf_embedder(self, minimal_invoice) -> None:
        from mcp_einvoicing_de.utils.pdf import embed_xml_in_pdf

        pdf_base = generate_pdf_invoice(minimal_invoice)
        xml_payload = b"<rsm:CrossIndustryInvoice xmlns:rsm='x'><test/></rsm:CrossIndustryInvoice>"
        hybrid = embed_xml_in_pdf(pdf_base, xml_payload, profile_name="EN_16931")
        extracted = _extract_xml_from_pdf(hybrid)
        assert extracted == xml_payload

    def test_missing_attachment_raises(self, minimal_invoice) -> None:
        from mcp_einvoicing_core.exceptions import EInvoicingError

        pdf_base = generate_pdf_invoice(minimal_invoice)
        with pytest.raises(EInvoicingError, match="No ZUGFeRD"):
            _extract_xml_from_pdf(pdf_base)


@_pikepdf_required
class TestParsePdfBase64Branch:
    @pytest.mark.asyncio
    async def test_pdf_branch_returns_structured_error_on_missing_attachment(
        self, minimal_invoice
    ) -> None:
        from mcp_einvoicing_de.tools.invoice_parse import invoice_parse

        pdf_base = generate_pdf_invoice(minimal_invoice)
        data = await invoice_parse(pdf_base64=base64.b64encode(pdf_base).decode("ascii"))
        assert "No ZUGFeRD" in data.get("error", "")
