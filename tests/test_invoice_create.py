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
        assert data["buyer_vat_id"] == "DE136695976"

    @pytest.mark.asyncio
    async def test_pdf_output_with_opt_in_succeeds(
        self, invoice_payload: dict
    ) -> None:
        result = await handle_invoice_create(
            {
                "invoice": invoice_payload,
                "output_format": "pdf",
                "transitional_period_opt_in": True,
            }
        )
        data = json.loads(result[0].text)
        assert "error" not in data
        assert "pdf_base64" in data or "xml_content" in data

    @pytest.mark.asyncio
    async def test_pdf_output_allowed_for_non_de_buyer(self) -> None:
        address = ZUGFeRDAddress(line_one="1 rue de la Paix", city="Paris", postcode="75001")
        seller = ZUGFeRDParty(name="Muster GmbH", address=address, vat_id="DE129273398")
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
        assert "error" not in data
        assert data["pdf_base64"] is not None


class TestTaxRepresentativeEmission:
    def test_bg11_block_emitted_after_buyer(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        address = ZUGFeRDAddress(line_one="2 rue Lafayette", city="Paris", postcode="75009")
        rep = ZUGFeRDParty(name="Fiscale Vertretung GmbH", address=address, vat_id="DE198765432")
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


# ---------------------------------------------------------------------------
# ARCH-VALID-1d — model-level USt-IdNr checksum enforcement on ZUGFeRDParty
# ---------------------------------------------------------------------------


class TestZUGFeRDPartyVatIdValidation:
    """ZUGFeRDParty.vat_id must enforce the DE mod-11 check digit for DE-prefixed VATs.

    Non-DE counterparty VATs (e.g. FR, IT) are accepted unchanged — those
    formats are out of scope for the German validator.
    """

    @staticmethod
    def _address() -> ZUGFeRDAddress:
        return ZUGFeRDAddress(line_one="Musterstr. 1", city="Berlin", postcode="10115")

    def test_invalid_de_vat_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="German USt-IdNr"):
            ZUGFeRDParty(name="X GmbH", address=self._address(), vat_id="DE123456789")

    def test_valid_de_vat_accepted(self) -> None:
        party = ZUGFeRDParty(
            name="X GmbH", address=self._address(), vat_id="DE129273398"
        )
        assert party.vat_id == "DE129273398"

    def test_non_de_vat_passes_through(self) -> None:
        party = ZUGFeRDParty(
            name="Buyer SAS", address=self._address(), vat_id="FR12345678901"
        )
        assert party.vat_id == "FR12345678901"

    def test_none_vat_id_allowed(self) -> None:
        party = ZUGFeRDParty(name="X GmbH", address=self._address())
        assert party.vat_id is None
