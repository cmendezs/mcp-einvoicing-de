"""Shared test fixtures for mcp-einvoicing-de tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from mcp_einvoicing_de.models.zugferd import (
    GermanTaxCategory,
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDParty,
    ZUGFeRDPaymentMeans,
    ZUGFeRDProfile,
    ZUGFeRDTax,
)


@pytest.fixture()
def minimal_invoice() -> ZUGFeRDInvoice:
    """Minimal valid ZUGFeRDInvoice covering MINIMUM profile required fields."""
    seller_address = ZUGFeRDAddress(line_one="Musterstraße 1", city="Berlin", postcode="10115")
    buyer_address = ZUGFeRDAddress(line_one="Beispielweg 5", city="München", postcode="80331")

    seller = ZUGFeRDParty(
        name="Muster GmbH",
        address=seller_address,
        vat_id="DE123456789",
    )
    buyer = ZUGFeRDParty(
        name="Käufer AG",
        address=buyer_address,
        vat_id="DE987654321",
    )
    tax = ZUGFeRDTax(
        category=GermanTaxCategory.STANDARD,
        rate=Decimal("19"),
        taxable_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
    )
    return ZUGFeRDInvoice(
        profile=ZUGFeRDProfile.MINIMUM,
        invoice_number="RE-2025-001",
        invoice_date=date(2025, 1, 15),
        seller=seller,
        buyer=buyer,
        sum_of_line_net_amounts=Decimal("100.00"),
        tax_exclusive_amount=Decimal("100.00"),
        tax_inclusive_amount=Decimal("119.00"),
        tax_total=Decimal("19.00"),
        amount_due=Decimal("119.00"),
        tax_lines=[tax],
        payment_means=ZUGFeRDPaymentMeans(
            type_code="58",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
        ),
    )


@pytest.fixture()
def minimal_cii_xml() -> bytes:
    """Minimal syntactically valid CII XML fragment for parser/validator tests.

    [NEED: replace with a real minimal ZUGFeRD MINIMUM CII XML]
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:factur-x.eu:1p0:minimum</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>RE-2025-001</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20250115</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty><ram:Name>Muster GmbH</ram:Name></ram:SellerTradeParty>
      <ram:BuyerTradeParty><ram:Name>Kaeufer AG</ram:Name></ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:TaxBasisTotalAmount>100.00</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount currencyID="EUR">19.00</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>119.00</ram:GrandTotalAmount>
        <ram:DuePayableAmount>119.00</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>""".encode("utf-8")
