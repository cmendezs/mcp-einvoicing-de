"""Tests for the invoice_create MCP tool: B2B mandate gate and BG-11 emission."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from mcp_einvoicing_de.models.zugferd import (
    GermanTaxCategory,
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDParty,
    ZUGFeRDProfile,
    ZUGFeRDTax,
)
from mcp_einvoicing_de.serializers import ZUGFeRDCIISerializer
from mcp_einvoicing_de.tools.invoice_create import (
    _buyer_requires_de_b2b_mandate,
    handle_invoice_create,
)


class TestBuyerMandateHelper:
    def test_de_vat_id_triggers_mandate(self) -> None:
        assert _buyer_requires_de_b2b_mandate("DE123456789") is True

    def test_lowercase_de_vat_id_is_normalised(self) -> None:
        assert _buyer_requires_de_b2b_mandate("de999999999") is True

    def test_non_de_vat_id_does_not_trigger(self) -> None:
        assert _buyer_requires_de_b2b_mandate("FR12345678901") is False

    def test_missing_vat_id_does_not_trigger(self) -> None:
        assert _buyer_requires_de_b2b_mandate(None) is False


class TestInvoiceCreateHandler:
    @pytest.fixture()
    def invoice_payload(self, minimal_invoice: ZUGFeRDInvoice) -> dict:
        # invoice_create expects a dict matching ZUGFeRDInvoice; use model_dump.
        return minimal_invoice.model_dump(mode="json")

    @pytest.mark.asyncio
    async def test_default_xml_output_succeeds(self, invoice_payload: dict) -> None:
        result = await handle_invoice_create({"invoice": invoice_payload})
        data = json.loads(result[0].text)
        assert "error" not in data
        assert "<rsm:CrossIndustryInvoice" in (data.get("xml_content") or "")

    @pytest.mark.asyncio
    async def test_pdf_output_rejected_for_de_buyer_without_opt_in(
        self, invoice_payload: dict
    ) -> None:
        result = await handle_invoice_create(
            {"invoice": invoice_payload, "output_format": "pdf"}
        )
        data = json.loads(result[0].text)
        assert "DE B2B mandate" in data["error"]
        assert data["buyer_vat_id"] == "DE987654321"

    @pytest.mark.asyncio
    async def test_pdf_output_with_opt_in_falls_through_to_unimplemented(
        self, invoice_payload: dict
    ) -> None:
        # transitional_period_opt_in bypasses the mandate check; PDF is still gated
        # because PDF/A-3 conformance is not yet complete.
        result = await handle_invoice_create(
            {
                "invoice": invoice_payload,
                "output_format": "pdf",
                "transitional_period_opt_in": True,
            }
        )
        data = json.loads(result[0].text)
        assert "PDF" in data["error"]
        assert "experimental" in data["error"]

    @pytest.mark.asyncio
    async def test_pdf_output_allowed_for_non_de_buyer(self) -> None:
        # Non-DE buyer is exempt from the structured-format mandate; the PDF path
        # still rejects because PDF/A-3 conformance is incomplete, but it is the
        # PDF gate, not the mandate gate, that fires.
        address = ZUGFeRDAddress(line_one="1 rue de la Paix", city="Paris", postcode="75001")
        seller = ZUGFeRDParty(name="Muster GmbH", address=address, vat_id="DE123456789")
        buyer = ZUGFeRDParty(name="Buyer SAS", address=address, vat_id="FR12345678901")
        tax = ZUGFeRDTax(
            category=GermanTaxCategory.STANDARD,
            rate=Decimal("19"),
            taxable_amount=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
        )
        invoice = ZUGFeRDInvoice(
            profile=ZUGFeRDProfile.MINIMUM,
            invoice_number="INV-1",
            invoice_date=date(2025, 2, 1),
            seller=seller,
            buyer=buyer,
            sum_of_line_net_amounts=Decimal("100.00"),
            tax_exclusive_amount=Decimal("100.00"),
            tax_inclusive_amount=Decimal("119.00"),
            tax_total=Decimal("19.00"),
            amount_due=Decimal("119.00"),
            tax_lines=[tax],
        )
        result = await handle_invoice_create(
            {"invoice": invoice.model_dump(mode="json"), "output_format": "pdf"}
        )
        data = json.loads(result[0].text)
        assert "DE B2B mandate" not in data.get("error", "")
        assert "PDF" in data["error"]


class TestTaxRepresentativeEmission:
    def test_bg11_block_emitted_after_buyer(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        address = ZUGFeRDAddress(line_one="2 rue Lafayette", city="Paris", postcode="75009")
        rep = ZUGFeRDParty(name="Fiscale Vertretung GmbH", address=address, vat_id="DE111111111")
        minimal_invoice.tax_representative = rep
        # Bump from MINIMUM to EN_16931 so a CII representative block is meaningful.
        minimal_invoice.profile = ZUGFeRDProfile.EN_16931

        xml = ZUGFeRDCIISerializer().serialize(minimal_invoice, pretty_print=False)
        text = xml.decode("utf-8")
        assert "SellerTaxRepresentativeTradeParty" in text
        assert "Fiscale Vertretung GmbH" in text
        # Order check: SellerTaxRepresentativeTradeParty must follow BuyerTradeParty.
        buyer_idx = text.index("BuyerTradeParty")
        rep_idx = text.index("SellerTaxRepresentativeTradeParty")
        assert rep_idx > buyer_idx
