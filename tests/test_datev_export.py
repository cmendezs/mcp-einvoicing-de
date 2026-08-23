"""Tests for the datev_export MCP tool (DE-TL-1, DE-TL-2, DE-TL-3).

DE-TL-1: BU-Schlüssel must be resolved per-line from the line's own
(tax_category, tax_rate), not from tax_lines[0] applied to every line —
the old behaviour mis-keyed reverse-charge lines as exempt.

DE-TL-2: Belegdatum must be zero-padded TTMM.

DE-TL-3: both the per-line and no-lines branches must post the invoice
gross amount (net + VAT), not net-only in the per-line branch.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

import pytest

from mcp_einvoicing_de.models.zugferd import (
    GermanTaxCategory,
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDLineItem,
    ZUGFeRDParty,
    ZUGFeRDProfile,
    ZUGFeRDTax,
)
from mcp_einvoicing_de.tools.datev_export import (
    _bu_key,
    _format_datev_date,
    _resolve_line_tax,
    datev_export,
)

_SELLER = ZUGFeRDParty(
    name="Muster GmbH",
    address=ZUGFeRDAddress(line_one="Musterstr. 1", city="Berlin", postcode="10115"),
    vat_id="DE129273398",
)
_BUYER = ZUGFeRDParty(
    name="Käufer AG",
    address=ZUGFeRDAddress(line_one="Beispielweg 5", city="München", postcode="80331"),
    vat_id="DE136695976",
)


def _line(
    line_id: str, net: Decimal, rate: Decimal, category: GermanTaxCategory
) -> ZUGFeRDLineItem:
    return ZUGFeRDLineItem(
        line_id=line_id,
        name=f"Line {line_id}",
        quantity=Decimal("1"),
        unit_code="C62",
        unit_price=net,
        line_net_amount=net,
        tax_rate=rate,
        tax_category=category,
    )


def _tax(rate: Decimal, category: GermanTaxCategory, taxable: Decimal) -> ZUGFeRDTax:
    tax_amount = (taxable * rate / Decimal("100")).quantize(Decimal("0.01"))
    return ZUGFeRDTax(category=category, rate=rate, taxable_amount=taxable, tax_amount=tax_amount)


# ── Unit tests — _bu_key / _resolve_line_tax ─────────────────────────────────


class TestBuKey:
    def test_standard_rate_revenue_has_no_automatik_bu(self) -> None:
        """Revenue-side postings at the standard/reduced rate carry no
        BU-Schlüssel — the correct SKR03/04 Erlöskonto (8400 vs 8300)
        encodes the rate, not the BU key. [Unverified]
        """
        assert _bu_key(GermanTaxCategory.STANDARD, Decimal("19"), "revenue") == ""
        assert _bu_key(GermanTaxCategory.REDUCED, Decimal("7"), "revenue") == ""

    def test_reverse_charge_is_not_mis_keyed_as_exempt(self) -> None:
        """DE-TL-1 regression: the old rate-only lookup mapped any 0%-rate
        line (including reverse charge) to BU "8" (tax-exempt). Reverse
        charge must resolve to its own code, distinct from plain exemption.
        """
        reverse_charge_bu = _bu_key(GermanTaxCategory.REVERSE_CHARGE, Decimal("0"), "revenue")
        exempt_bu = _bu_key(GermanTaxCategory.EXEMPT, Decimal("0"), "revenue")
        assert reverse_charge_bu == "94"
        assert exempt_bu == ""
        assert reverse_charge_bu != exempt_bu

    def test_intra_community_supply_bu(self) -> None:
        assert _bu_key(GermanTaxCategory.INTRA_COMMUNITY, Decimal("0"), "revenue") == "91"

    def test_expense_side_standard_rate_differs_by_rate(self) -> None:
        assert _bu_key(GermanTaxCategory.STANDARD, Decimal("19"), "expense") == "9"
        assert _bu_key(GermanTaxCategory.STANDARD, Decimal("7"), "expense") == "8"


class TestResolveLineTax:
    def test_matches_line_to_its_own_tax_lines_entry(self) -> None:
        tax_lines = [
            _tax(Decimal("19"), GermanTaxCategory.STANDARD, Decimal("100.00")),
            _tax(Decimal("7"), GermanTaxCategory.STANDARD, Decimal("50.00")),
        ]
        line_19 = _line("1", Decimal("100.00"), Decimal("19"), GermanTaxCategory.STANDARD)
        line_7 = _line("2", Decimal("50.00"), Decimal("7"), GermanTaxCategory.REDUCED)

        _, rate_19 = _resolve_line_tax(line_19, tax_lines)
        _, rate_7 = _resolve_line_tax(line_7, tax_lines)

        assert rate_19 == Decimal("19")
        assert rate_7 == Decimal("7")

    def test_falls_back_to_first_tax_line_when_unmatched(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        tax_lines = [_tax(Decimal("19"), GermanTaxCategory.STANDARD, Decimal("100.00"))]
        # A line whose declared rate (16%) matches no entry in tax_lines —
        # a degraded/inconsistent input the resolver must not crash on.
        mismatched_line = _line("1", Decimal("100.00"), Decimal("16"), GermanTaxCategory.STANDARD)

        with caplog.at_level(logging.WARNING):
            category, rate = _resolve_line_tax(mismatched_line, tax_lines)

        assert rate == Decimal("19")
        assert category == GermanTaxCategory.STANDARD
        assert any("falling back to tax_lines[0]" in r.message for r in caplog.records)


# ── Unit tests — Belegdatum (DE-TL-2) ────────────────────────────────────────


class TestBelegdatum:
    def test_zero_padded_ttmm(self) -> None:
        assert _format_datev_date(date(2026, 1, 2)) == "0201"

    def test_double_digit_day_and_month(self) -> None:
        assert _format_datev_date(date(2026, 12, 25)) == "2512"


# ── Integration tests — handle_datev_export ──────────────────────────────────


def _make_invoice(*, with_lines: bool) -> ZUGFeRDInvoice:
    tax = _tax(Decimal("19"), GermanTaxCategory.STANDARD, Decimal("1000.00"))
    lines = (
        [_line("1", Decimal("1000.00"), Decimal("19"), GermanTaxCategory.STANDARD)]
        if with_lines
        else []
    )
    return ZUGFeRDInvoice(
        profile=ZUGFeRDProfile.EN_16931,
        invoice_number="RE-2026-DATEV-001",
        invoice_date=date(2026, 1, 2),
        seller=_SELLER,
        buyer=_BUYER,
        sum_of_line_net_amounts=Decimal("1000.00"),
        tax_exclusive_amount=Decimal("1000.00"),
        tax_inclusive_amount=Decimal("1190.00"),
        tax_total=Decimal("190.00"),
        amount_due=Decimal("1190.00"),
        tax_lines=[tax],
        line_items=lines,
    )


class TestHandleDatevExportGrossPosting:
    @pytest.mark.asyncio
    async def test_both_branches_post_the_same_gross_amount(self) -> None:
        with_lines_result = await datev_export(
            invoice=_make_invoice(with_lines=True).model_dump(mode="json")
        )
        no_lines_result = await datev_export(
            invoice=_make_invoice(with_lines=False).model_dump(mode="json")
        )
        with_lines_csv = with_lines_result["csv_content"]
        no_lines_csv = no_lines_result["csv_content"]

        with_lines_amount = with_lines_csv.splitlines()[1].split(";")[0]
        no_lines_amount = no_lines_csv.splitlines()[1].split(";")[0]

        assert with_lines_amount == "1190.00"
        assert no_lines_amount == "1190.00"
        assert with_lines_amount == no_lines_amount

    @pytest.mark.asyncio
    async def test_belegdatum_in_csv_is_zero_padded(self) -> None:
        result = await datev_export(invoice=_make_invoice(with_lines=True).model_dump(mode="json"))
        csv_content = result["csv_content"]
        belegdatum = csv_content.splitlines()[1].split(";")[9]
        assert belegdatum == "0201"
