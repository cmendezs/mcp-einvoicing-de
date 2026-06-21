"""Tests for invoice_convert: profile URN rewrite and downgrade gating."""

from __future__ import annotations

import json

import pytest

from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile
from mcp_einvoicing_de.serializers import ZUGFeRDCIISerializer
from mcp_einvoicing_de.tools.invoice_convert import handle_invoice_convert


@pytest.fixture()
def en16931_cii_xml(minimal_invoice: ZUGFeRDInvoice) -> bytes:
    invoice = minimal_invoice.model_copy(update={"profile": ZUGFeRDProfile.EN_16931})
    return ZUGFeRDCIISerializer().serialize(invoice, pretty_print=False)


class TestInvoiceConvertHandler:
    @pytest.mark.asyncio
    async def test_profile_urn_swap_same_syntax(self, en16931_cii_xml: bytes) -> None:
        result = await handle_invoice_convert(
            {
                "xml_content": en16931_cii_xml.decode("utf-8"),
                "target_profile": "EXTENDED",
                "target_syntax": "CII",
            }
        )
        data = json.loads(result[0].text)
        assert data["source_profile"] == "EN_16931"
        assert data["target_profile"] == "EXTENDED"
        assert ZUGFeRDProfile.EXTENDED.value in data["xml_content"]
        assert data["data_loss_warnings"] == []

    @pytest.mark.asyncio
    async def test_downgrade_to_minimum_without_opt_in_is_rejected(
        self, minimal_invoice: ZUGFeRDInvoice
    ) -> None:
        # Add a line item to force the downgrade rejection path.
        from decimal import Decimal

        from mcp_einvoicing_de.models.zugferd import (
            GermanTaxCategory,
            ZUGFeRDLineItem,
        )

        invoice = minimal_invoice.model_copy(update={"profile": ZUGFeRDProfile.EN_16931})
        invoice.line_items = [
            ZUGFeRDLineItem(
                line_id="1",
                name="Beratung",
                quantity=Decimal("1"),
                unit_code="HUR",
                unit_price=Decimal("100.00"),
                line_net_amount=Decimal("100.00"),
                tax_category=GermanTaxCategory.STANDARD,
                tax_rate=Decimal("19"),
            )
        ]
        xml = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=False)

        result = await handle_invoice_convert(
            {
                "xml_content": xml.decode("utf-8"),
                "target_profile": "MINIMUM",
                "target_syntax": "CII",
            }
        )
        data = json.loads(result[0].text)
        assert "allow_data_loss" in data["error"]

    @pytest.mark.asyncio
    async def test_cross_syntax_is_rejected(self, en16931_cii_xml: bytes) -> None:
        result = await handle_invoice_convert(
            {
                "xml_content": en16931_cii_xml.decode("utf-8"),
                "target_profile": "XRECHNUNG",
                "target_syntax": "UBL",
            }
        )
        data = json.loads(result[0].text)
        assert "Cross-syntax conversion" in data["error"]
