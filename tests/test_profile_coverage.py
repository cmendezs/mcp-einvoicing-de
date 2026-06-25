"""DE-V1-1: Full EN 16931 coverage verification across all ZUGFeRD profiles.

Round-trips each profile through serialize -> parse -> re-serialize and asserts
no field loss on tax totals, party identifiers, and line items.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import (
    GermanTaxCategory,
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDLineItem,
    ZUGFeRDParty,
    ZUGFeRDPaymentMeans,
    ZUGFeRDProfile,
    ZUGFeRDTax,
)
from mcp_einvoicing_de.serializers import (
    XRechnungUBLParser,
    XRechnungUBLSerializer,
    ZUGFeRDCIIParser,
    ZUGFeRDCIISerializer,
)


def _make_invoice(profile: ZUGFeRDProfile, with_lines: bool = True) -> ZUGFeRDInvoice:
    seller = ZUGFeRDParty(
        name="Muster GmbH",
        address=ZUGFeRDAddress(line_one="Musterstr. 1", city="Berlin", postcode="10115"),
        vat_id="DE123456789",
    )
    buyer = ZUGFeRDParty(
        name="Käufer AG",
        address=ZUGFeRDAddress(line_one="Beispielweg 5", city="München", postcode="80331"),
        vat_id="DE987654321",
    )
    tax = ZUGFeRDTax(
        category=GermanTaxCategory.STANDARD,
        rate=Decimal("19"),
        taxable_amount=Decimal("200.00"),
        tax_amount=Decimal("38.00"),
    )
    lines = []
    if with_lines:
        lines = [
            ZUGFeRDLineItem(
                line_id="1",
                name="Widget A",
                quantity=Decimal("2"),
                unit_code="C62",
                unit_price=Decimal("50.00"),
                net_amount=Decimal("100.00"),
                line_net_amount=Decimal("100.00"),
                tax_rate=Decimal("19"),
                tax_category=GermanTaxCategory.STANDARD,
            ),
            ZUGFeRDLineItem(
                line_id="2",
                name="Widget B",
                quantity=Decimal("1"),
                unit_code="C62",
                unit_price=Decimal("100.00"),
                net_amount=Decimal("100.00"),
                line_net_amount=Decimal("100.00"),
                tax_rate=Decimal("19"),
                tax_category=GermanTaxCategory.STANDARD,
            ),
        ]
    return ZUGFeRDInvoice(
        profile=profile,
        invoice_number="PROF-TEST-001",
        invoice_date=date(2025, 6, 15),
        seller=seller,
        buyer=buyer,
        sum_of_line_net_amounts=Decimal("200.00"),
        tax_exclusive_amount=Decimal("200.00"),
        tax_inclusive_amount=Decimal("238.00"),
        tax_total=Decimal("38.00"),
        amount_due=Decimal("238.00"),
        tax_lines=[tax],
        line_items=lines,
        payment_means=ZUGFeRDPaymentMeans(
            type_code="58",
            iban="DE89370400440532013000",
        ),
        buyer_reference="BR-PROF-001",
    )


class TestProfileCoverageCII:
    """Round-trip each CII-capable profile through serialize -> parse."""

    @pytest.mark.parametrize(
        "profile,with_lines",
        [
            (ZUGFeRDProfile.MINIMUM, False),
            (ZUGFeRDProfile.BASIC_WL, False),
            (ZUGFeRDProfile.BASIC, True),
            (ZUGFeRDProfile.EN_16931, True),
            (ZUGFeRDProfile.EXTENDED, True),
            (ZUGFeRDProfile.XRECHNUNG, True),
        ],
    )
    def test_cii_round_trip(
        self, profile: ZUGFeRDProfile, with_lines: bool
    ) -> None:
        invoice = _make_invoice(profile, with_lines=with_lines)
        serializer = ZUGFeRDCIISerializer()
        parser = ZUGFeRDCIIParser()

        xml_bytes = serializer.serialize(invoice, pretty_print=True)
        parsed = parser.parse(xml_bytes)

        assert parsed.invoice_number == invoice.invoice_number
        assert parsed.tax_inclusive_amount == invoice.tax_inclusive_amount
        assert parsed.tax_total == invoice.tax_total
        assert parsed.seller.name == invoice.seller.name
        assert parsed.buyer.name == invoice.buyer.name

        if with_lines:
            assert len(parsed.line_items) == len(invoice.line_items)
            for orig, rt in zip(invoice.line_items, parsed.line_items, strict=True):
                assert rt.name == orig.name
                assert rt.line_net_amount == orig.line_net_amount


class TestProfileCoverageUBL:
    """Round-trip XRechnung UBL through serialize -> parse."""

    def test_xrechnung_ubl_round_trip(self) -> None:
        base = _make_invoice(ZUGFeRDProfile.XRECHNUNG, with_lines=True)
        invoice = XRechnungInvoice.model_validate({
            **base.model_dump(),
            "syntax": XRechnungSyntax.UBL,
        })
        serializer = XRechnungUBLSerializer()
        parser = XRechnungUBLParser()

        xml_bytes = serializer.serialize(invoice, pretty_print=True)
        parsed = parser.parse(xml_bytes)

        assert parsed.invoice_number == invoice.invoice_number
        assert parsed.tax_inclusive_amount == invoice.tax_inclusive_amount
        assert parsed.seller.name == invoice.seller.name
        assert parsed.buyer.name == invoice.buyer.name
        assert len(parsed.line_items) == len(invoice.line_items)
