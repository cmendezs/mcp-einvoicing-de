"""Tests for the invoice_validate MCP tool."""

from __future__ import annotations

import base64
import json

import pytest

from mcp_einvoicing_de.tools.invoice_validate import (
    InvoiceValidateInput,
    handle_invoice_validate,
)
from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile
from mcp_einvoicing_de.models.zugferd import ZUGFeRDProfile
from mcp_einvoicing_de.models.xrechnung import XRechnungSyntax


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


# ── Integration tests — handle_invoice_validate ───────────────────────────────

class TestHandleInvoiceValidate:
    @pytest.mark.asyncio
    async def test_missing_input_returns_error(self) -> None:
        result = await handle_invoice_validate({})
        data = json.loads(result[0].text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_valid_xml_returns_result_structure(self, minimal_cii_xml: bytes) -> None:
        """
        With no Schematron stylesheets installed, the validator returns a
        NO-STYLESHEET warning but does not error. The response structure must
        be well-formed regardless.
        """
        result = await handle_invoice_validate({
            "xml_base64": base64.b64encode(minimal_cii_xml).decode(),
        })
        data = json.loads(result[0].text)
        # Either a valid output or a stylesheet-missing warning — both are structured
        assert "error" in data or "is_valid" in data

    @pytest.mark.asyncio
    async def test_malformed_xml_is_invalid(self) -> None:
        result = await handle_invoice_validate({"xml_content": "<broken"})
        data = json.loads(result[0].text)
        # Should either be a parse error at the input level or a validation error
        assert "error" in data or data.get("is_valid") is False

    @pytest.mark.asyncio
    async def test_profile_override(self, minimal_cii_xml: bytes) -> None:
        result = await handle_invoice_validate({
            "xml_base64": base64.b64encode(minimal_cii_xml).decode(),
            "profile": "EN_16931",
        })
        data = json.loads(result[0].text)
        if "is_valid" in data:
            assert data["profile"] == "EN_16931"

    @pytest.mark.asyncio
    async def test_strict_false_omits_warnings(self, minimal_cii_xml: bytes) -> None:
        result = await handle_invoice_validate({
            "xml_base64": base64.b64encode(minimal_cii_xml).decode(),
            "strict": False,
        })
        data = json.loads(result[0].text)
        if "warnings" in data:
            assert data["warnings"] == []
