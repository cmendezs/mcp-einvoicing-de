"""DE-SF-2: PDF/A-3 OutputIntent must embed a real sRGB ICC profile, not a
128-byte header-only stub."""

from __future__ import annotations

import importlib.util
from io import BytesIO

import pytest

from mcp_einvoicing_de.utils.pdf import _load_srgb_icc_bytes, generate_pdf_invoice

_PIKEPDF_AVAILABLE = importlib.util.find_spec("pikepdf") is not None
_pikepdf_required = pytest.mark.skipif(
    not _PIKEPDF_AVAILABLE,
    reason="pikepdf extra not installed (install with mcp-einvoicing-de[pdf])",
)


class TestIccProfileBytes:
    def test_icc_profile_is_not_the_old_128_byte_stub(self) -> None:
        icc_bytes = _load_srgb_icc_bytes()
        assert len(icc_bytes) != 128
        assert len(icc_bytes) > 1000

    def test_icc_profile_has_acsp_signature(self) -> None:
        icc_bytes = _load_srgb_icc_bytes()
        assert icc_bytes[36:40] == b"acsp"

    def test_icc_profile_declares_rgb_monitor_class(self) -> None:
        icc_bytes = _load_srgb_icc_bytes()
        assert icc_bytes[12:16] == b"mntr"
        assert icc_bytes[16:20] == b"RGB "


@_pikepdf_required
class TestOutputIntentEmbedsRealProfile:
    def test_output_intent_stream_matches_icc_file_length(self, minimal_invoice) -> None:
        import pikepdf

        pdf_bytes = generate_pdf_invoice(minimal_invoice)
        icc_bytes = _load_srgb_icc_bytes()

        with pikepdf.open(BytesIO(pdf_bytes)) as pdf:
            output_intents = pdf.Root["/OutputIntents"]
            assert len(output_intents) == 1
            dest_profile = output_intents[0]["/DestOutputProfile"]
            embedded_bytes = dest_profile.read_bytes()

        assert len(embedded_bytes) == len(icc_bytes)
        assert embedded_bytes == icc_bytes
