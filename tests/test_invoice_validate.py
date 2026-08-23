"""Tests for the invoice_validate MCP tool."""

from __future__ import annotations

import base64

import pytest

import mcp_einvoicing_de.tools.invoice_validate as invoice_validate_module
from mcp_einvoicing_de.models.xrechnung import XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import ZUGFeRDProfile
from mcp_einvoicing_de.tools.invoice_validate import (
    InvoiceValidateInput,
    invoice_validate,
)
from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile
from mcp_einvoicing_de.validators.schematron import ValidationResult


class _RecordingKoSIT:
    """Stand-in for KoSITValidator that records construction/calls with no HTTP."""

    instances: int = 0
    validate_calls: int = 0
    _UNVERIFIED_DEFAULT_KOSIT_URL = "https://validator.kosit.de/api/v1/validate"

    def __init__(self, *args: object, **kwargs: object) -> None:
        type(self).instances += 1

    async def validate(self, xml_bytes: bytes, filename: str = "invoice.xml") -> ValidationResult:
        type(self).validate_calls += 1
        return ValidationResult(is_valid=True)


# ── Unit tests — input model ──────────────────────────────────────────────────


class TestInvoiceValidateInput:
    def test_xml_content_accepted(self) -> None:
        inp = InvoiceValidateInput(xml_content="<Invoice/>")
        assert inp.get_xml_bytes() == b"<Invoice/>"

    def test_xml_base64_accepted(self) -> None:
        raw = b"<Invoice/>"
        inp = InvoiceValidateInput(xml_base64=base64.b64encode(raw).decode())
        assert inp.get_xml_bytes() == raw

    def test_both_absent_raises(self) -> None:
        inp = InvoiceValidateInput()
        with pytest.raises(ValueError, match="xml_content or xml_base64"):
            inp.get_xml_bytes()

    def test_invalid_base64_raises(self) -> None:
        inp = InvoiceValidateInput(xml_base64="not-valid-base64!!!")
        with pytest.raises(ValueError, match="not valid base64"):
            inp.get_xml_bytes()


# ── Unit tests — XML detection helpers ───────────────────────────────────────


class TestDetectInvoiceSyntax:
    def test_detects_cii(self, minimal_cii_xml: bytes) -> None:
        syntax = detect_invoice_syntax(minimal_cii_xml)
        assert syntax == XRechnungSyntax.CII

    def test_detects_ubl(self) -> None:
        ubl_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>TEST-001</cbc:ID>
</Invoice>"""
        syntax = detect_invoice_syntax(ubl_xml)
        assert syntax == XRechnungSyntax.UBL

    def test_invalid_xml_raises(self) -> None:
        with pytest.raises(ValueError):
            detect_invoice_syntax(b"not xml at all")

    def test_unknown_namespace_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot determine"):
            detect_invoice_syntax(b"<root xmlns='urn:unknown'/>")


class TestDetectZUGFeRDProfile:
    def test_detects_minimum(self, minimal_cii_xml: bytes) -> None:
        profile = detect_zugferd_profile(minimal_cii_xml)
        assert profile == ZUGFeRDProfile.MINIMUM

    def test_returns_none_for_unknown(self) -> None:
        xml = b"""<?xml version="1.0"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:unknown:profile</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
</rsm:CrossIndustryInvoice>"""
        profile = detect_zugferd_profile(xml)
        assert profile is None

    def test_returns_none_for_invalid_xml(self) -> None:
        profile = detect_zugferd_profile(b"not xml")
        assert profile is None

    def test_detects_xrechnung_ubl_invoice(self) -> None:
        ubl_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0</cbc:CustomizationID>
  <cbc:ID>TEST-001</cbc:ID>
</Invoice>"""
        profile = detect_zugferd_profile(ubl_xml)
        assert profile == ZUGFeRDProfile.XRECHNUNG

    def test_detects_xrechnung_ubl_creditnote(self) -> None:
        ubl_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0</cbc:CustomizationID>
  <cbc:ID>CN-001</cbc:ID>
</CreditNote>"""
        profile = detect_zugferd_profile(ubl_xml)
        assert profile == ZUGFeRDProfile.XRECHNUNG


# ── Integration tests — handle_invoice_validate ───────────────────────────────


class TestHandleInvoiceValidate:
    @pytest.mark.asyncio
    async def test_missing_input_returns_error(self) -> None:
        data = await invoice_validate()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_valid_xml_returns_result_structure(self, minimal_cii_xml: bytes) -> None:
        """
        With no Schematron stylesheets installed, the validator returns a
        NO-STYLESHEET warning but does not error. The response structure must
        be well-formed regardless.
        """
        data = await invoice_validate(xml_base64=base64.b64encode(minimal_cii_xml).decode())
        # Either a valid output or a stylesheet-missing warning — both are structured
        assert "error" in data or "is_valid" in data

    @pytest.mark.asyncio
    async def test_malformed_xml_is_invalid(self) -> None:
        data = await invoice_validate(xml_content="<broken")
        # Should either be a parse error at the input level or a validation error
        assert "error" in data or data.get("is_valid") is False

    @pytest.mark.asyncio
    async def test_profile_override(self, minimal_cii_xml: bytes) -> None:
        data = await invoice_validate(
            xml_base64=base64.b64encode(minimal_cii_xml).decode(),
            profile="EN_16931",
        )
        if "is_valid" in data:
            assert data["profile"] == "EN_16931"

    @pytest.mark.asyncio
    async def test_strict_false_omits_warnings(self, minimal_cii_xml: bytes) -> None:
        data = await invoice_validate(
            xml_base64=base64.b64encode(minimal_cii_xml).decode(),
            strict=False,
        )
        if "warnings" in data:
            assert data["warnings"] == []


# ── DE-LC-1: cloud validation is opt-in, default is local-only ───────────────


class TestCloudValidateOptIn:
    @pytest.fixture(autouse=True)
    def _patch_kosit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _RecordingKoSIT.instances = 0
        _RecordingKoSIT.validate_calls = 0
        monkeypatch.setattr(invoice_validate_module, "KoSITValidator", _RecordingKoSIT)

    @pytest.mark.asyncio
    async def test_default_call_makes_no_kosit_call(self, minimal_cii_xml: bytes) -> None:
        data = await invoice_validate(xml_base64=base64.b64encode(minimal_cii_xml).decode())
        assert _RecordingKoSIT.instances == 0
        assert _RecordingKoSIT.validate_calls == 0
        assert data.get("validator_used") == "local_schematron"

    @pytest.mark.asyncio
    async def test_cloud_validate_true_calls_kosit(self, minimal_cii_xml: bytes) -> None:
        data = await invoice_validate(
            xml_base64=base64.b64encode(minimal_cii_xml).decode(),
            cloud_validate=True,
        )
        assert _RecordingKoSIT.instances == 1
        assert _RecordingKoSIT.validate_calls == 1
        assert data.get("validator_used") == "kosit_cloud"

    @pytest.mark.asyncio
    async def test_deprecated_use_local_only_true_avoids_kosit_and_warns(
        self, minimal_cii_xml: bytes
    ) -> None:
        with pytest.warns(DeprecationWarning, match="use_local_only is deprecated"):
            data = await invoice_validate(
                xml_base64=base64.b64encode(minimal_cii_xml).decode(),
                use_local_only=True,
            )
        assert _RecordingKoSIT.instances == 0
        assert data.get("validator_used") == "local_schematron"

    @pytest.mark.asyncio
    async def test_deprecated_use_local_only_false_opts_into_cloud(
        self, minimal_cii_xml: bytes
    ) -> None:
        with pytest.warns(DeprecationWarning, match="use_local_only is deprecated"):
            data = await invoice_validate(
                xml_base64=base64.b64encode(minimal_cii_xml).decode(),
                use_local_only=False,
            )
        assert _RecordingKoSIT.instances == 1
        assert data.get("validator_used") == "kosit_cloud"
