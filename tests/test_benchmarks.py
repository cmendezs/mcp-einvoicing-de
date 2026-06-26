"""DE-V1-3: Performance benchmarks for core invoice operations.

Requires pytest-benchmark: pip install pytest-benchmark
Run with: pytest tests/test_benchmarks.py --benchmark-only
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

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
from mcp_einvoicing_de.serializers import ZUGFeRDCIIParser, ZUGFeRDCIISerializer
from mcp_einvoicing_de.utils.pdf import generate_pdf_invoice

pytest.importorskip("pytest_benchmark")


def _invoice_with_lines(n_lines: int = 10) -> ZUGFeRDInvoice:
    seller = ZUGFeRDParty(
        name="Bench GmbH",
        address=ZUGFeRDAddress(line_one="Teststr. 1", city="Berlin", postcode="10115"),
        vat_id="DE129273398",
    )
    buyer = ZUGFeRDParty(
        name="Bench Käufer AG",
        address=ZUGFeRDAddress(line_one="Weg 2", city="München", postcode="80331"),
        vat_id="DE136695976",
    )
    lines = [
        ZUGFeRDLineItem(
            line_id=str(i + 1),
            name=f"Item {i + 1}",
            quantity=Decimal("1"),
            unit_code="C62",
            unit_price=Decimal("10.00"),
            line_net_amount=Decimal("10.00"),
            tax_category=GermanTaxCategory.STANDARD,
            tax_rate=Decimal("19"),
        )
        for i in range(n_lines)
    ]
    net = Decimal("10.00") * n_lines
    tax_amount = (net * Decimal("19") / Decimal("100")).quantize(Decimal("0.01"))
    return ZUGFeRDInvoice(
        profile=ZUGFeRDProfile.EN_16931,
        invoice_number="BENCH-001",
        invoice_date=date(2025, 6, 1),
        seller=seller,
        buyer=buyer,
        sum_of_line_net_amounts=net,
        tax_exclusive_amount=net,
        tax_inclusive_amount=net + tax_amount,
        tax_total=tax_amount,
        amount_due=net + tax_amount,
        tax_lines=[
            ZUGFeRDTax(
                category=GermanTaxCategory.STANDARD,
                rate=Decimal("19"),
                taxable_amount=net,
                tax_amount=tax_amount,
            )
        ],
        line_items=lines,
        payment_means=ZUGFeRDPaymentMeans(type_code="58", iban="DE89370400440532013000"),
    )


class TestBenchmarks:
    def test_bench_invoice_create_serialize(self, benchmark: object) -> None:
        invoice = _invoice_with_lines(10)
        serializer = ZUGFeRDCIISerializer()
        benchmark(serializer.serialize, invoice, pretty_print=False)  # type: ignore[operator]

    def test_bench_invoice_parse(self, benchmark: object) -> None:
        invoice = _invoice_with_lines(10)
        xml_bytes = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=False)
        parser = ZUGFeRDCIIParser()
        benchmark(parser.parse, xml_bytes)  # type: ignore[operator]

    def test_bench_pdf_generate(self, benchmark: object) -> None:
        invoice = _invoice_with_lines(5)
        benchmark(generate_pdf_invoice, invoice)  # type: ignore[operator]

    def test_bench_round_trip(self, benchmark: object) -> None:
        invoice = _invoice_with_lines(10)
        serializer = ZUGFeRDCIISerializer()
        parser = ZUGFeRDCIIParser()

        def _round_trip() -> None:
            xml = serializer.serialize(invoice, pretty_print=False)
            parser.parse(xml)

        benchmark(_round_trip)  # type: ignore[operator]
