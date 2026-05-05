"""Tests for Pydantic models (ZUGFeRD and XRechnung)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import (
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDParty,
    ZUGFeRDProfile,
)


class TestZUGFeRDAddress:
    def test_default_country(self) -> None:
        addr = ZUGFeRDAddress(line_one="Str. 1", city="Berlin", postcode="10115")
        assert addr.country_code == "DE"

    def test_country_code_length_validation(self) -> None:
        with pytest.raises(ValidationError):
            ZUGFeRDAddress(line_one="Str. 1", city="Paris", postcode="75001", country_code="FRA")


class TestZUGFeRDInvoice:
    def test_minimal_invoice_builds(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        assert minimal_invoice.invoice_number == "RE-2025-001"
        assert minimal_invoice.profile == ZUGFeRDProfile.MINIMUM
        assert minimal_invoice.tax_inclusive_amount == Decimal("119.00")

    def test_tax_lines_required(self) -> None:
        with pytest.raises(ValidationError):
            ZUGFeRDInvoice(
                profile=ZUGFeRDProfile.MINIMUM,
                invoice_number="X",
                invoice_date=date(2025, 1, 1),
                seller=ZUGFeRDParty(
                    name="S",
                    address=ZUGFeRDAddress(line_one="A", city="B", postcode="12345"),
                ),
                buyer=ZUGFeRDParty(
                    name="B",
                    address=ZUGFeRDAddress(line_one="C", city="D", postcode="54321"),
                ),
                sum_of_line_net_amounts=Decimal("0"),
                tax_exclusive_amount=Decimal("0"),
                tax_inclusive_amount=Decimal("0"),
                tax_total=Decimal("0"),
                amount_due=Decimal("0"),
                tax_lines=[],  # Must have at least one
            )


class TestXRechnungInvoice:
    def test_profile_forced_to_xrechnung(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        data = minimal_invoice.model_dump()
        data["profile"] = ZUGFeRDProfile.EN_16931
        data["buyer_reference"] = "991-1234512345-06"
        xr = XRechnungInvoice.model_validate(data)
        assert xr.profile == ZUGFeRDProfile.XRECHNUNG

    def test_default_syntax_is_cii(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        data = minimal_invoice.model_dump()
        data["buyer_reference"] = "991-1234512345-06"
        xr = XRechnungInvoice.model_validate(data)
        assert xr.syntax == XRechnungSyntax.CII
