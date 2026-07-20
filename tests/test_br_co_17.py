"""DE-SC-3: BR-CO-17 — tax_amount must match taxable_amount * rate / 100."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from mcp_einvoicing_de.models.zugferd import GermanTaxCategory, ZUGFeRDTax


class TestBrCo17:
    def test_exact_amount_passes(self) -> None:
        tax = ZUGFeRDTax(
            category=GermanTaxCategory.STANDARD,
            rate=Decimal("19"),
            taxable_amount=Decimal("100.00"),
            tax_amount=Decimal("19.00"),
        )
        assert tax.tax_amount == Decimal("19.00")

    def test_within_tolerance_passes(self) -> None:
        # 33.33 * 19 / 100 = 6.3327 -> expected 6.33; 6.34 is within 0.01 tolerance.
        tax = ZUGFeRDTax(
            category=GermanTaxCategory.STANDARD,
            rate=Decimal("19"),
            taxable_amount=Decimal("33.33"),
            tax_amount=Decimal("6.34"),
        )
        assert tax.tax_amount == Decimal("6.34")

    def test_over_tolerance_raises(self) -> None:
        with pytest.raises(ValidationError, match="BR-CO-17"):
            ZUGFeRDTax(
                category=GermanTaxCategory.STANDARD,
                rate=Decimal("19"),
                taxable_amount=Decimal("100.00"),
                tax_amount=Decimal("25.00"),
            )
