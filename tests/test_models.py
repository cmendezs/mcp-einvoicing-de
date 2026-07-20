"""Tests for Pydantic models (ZUGFeRD and XRechnung) and Leitweg-ID validation."""

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
from mcp_einvoicing_de.utils.leitweg import looks_like_leitweg_id, validate_leitweg_id


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
        data["buyer_reference"] = "991-1234512345-01"
        xr = XRechnungInvoice.model_validate(data)
        assert xr.profile == ZUGFeRDProfile.XRECHNUNG

    def test_default_syntax_is_cii(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        data = minimal_invoice.model_dump()
        data["buyer_reference"] = "991-1234512345-01"
        xr = XRechnungInvoice.model_validate(data)
        assert xr.syntax == XRechnungSyntax.CII

    def test_buyer_reference_invalid_leitweg_rejected_when_b2g(
        self, minimal_invoice: ZUGFeRDInvoice
    ) -> None:
        """DE-SF-3: a bad check digit is only rejected in a B2G context, i.e.
        when the buyer party carries an explicit ``leitweg_id``.
        """
        data = minimal_invoice.model_dump()
        data["buyer"]["leitweg_id"] = "991-1234512345-01"
        data["buyer_reference"] = "991-1234512345-06"  # mod-97 = 6, not 1
        with pytest.raises(ValidationError, match="check digit"):
            XRechnungInvoice.model_validate(data)

    def test_buyer_reference_free_form_accepted(
        self, minimal_invoice: ZUGFeRDInvoice
    ) -> None:
        """Non-Leitweg-ID buyer reference strings must be accepted without format checks."""
        data = minimal_invoice.model_dump()
        data["buyer_reference"] = "PO-2025-98765"  # purchase order, not a Leitweg-ID
        xr = XRechnungInvoice.model_validate(data)
        assert xr.buyer_reference == "PO-2025-98765"

    def test_b2b_po_shaped_like_leitweg_not_false_matched(
        self, minimal_invoice: ZUGFeRDInvoice
    ) -> None:
        """DE-SF-3 regression: a B2B purchase-order reference that happens to
        match the Leitweg-ID shape (including a check digit that would be
        invalid as a real Leitweg-ID) must be accepted when the buyer party
        has no ``leitweg_id`` set — it is not a routing identifier here.
        """
        data = minimal_invoice.model_dump()
        assert data["buyer"].get("leitweg_id") is None
        data["buyer_reference"] = "04011000-12345-67"  # looks like a Leitweg-ID, bad check digit
        xr = XRechnungInvoice.model_validate(data)
        assert xr.buyer_reference == "04011000-12345-67"

    def test_b2g_valid_leitweg_accepted(self, minimal_invoice: ZUGFeRDInvoice) -> None:
        data = minimal_invoice.model_dump()
        data["buyer"]["leitweg_id"] = "991-1234512345-01"
        data["buyer_reference"] = "991-1234512345-01"
        xr = XRechnungInvoice.model_validate(data)
        assert xr.buyer_reference == "991-1234512345-01"


class TestLeitwegIdValidator:
    """Unit tests for validate_leitweg_id and looks_like_leitweg_id."""

    # Known-valid Leitweg-IDs (mod-97 = 1, computed and verified):
    VALID = [
        "04011000-12345-03",   # Verwaltungsebene 8 digits + Instanzkennzeichen
        "991-1234512345-01",   # 3-digit Verwaltungsebene + Instanzkennzeichen
        "991-01-03",           # Short Instanzkennzeichen
    ]

    INVALID_FORMAT = [
        "",                     # empty
        "abc-12345-06",        # Verwaltungsebene not all digits
        "04011000-12345",       # missing check digit segment
        "04011000-12345-1",    # check digit must be exactly 2 digits
        "04011000-12345-034",  # check digit must be exactly 2 digits
    ]

    INVALID_CHECKDIGIT = [
        "991-1234512345-06",   # mod-97 = 6
        "04011000-12345-34",   # FeRD synthetic example, mod-97 = 32
    ]

    @pytest.mark.parametrize("value", VALID)
    def test_valid_passes(self, value: str) -> None:
        assert validate_leitweg_id(value) == value

    @pytest.mark.parametrize("value", INVALID_FORMAT)
    def test_invalid_format_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="format"):
            validate_leitweg_id(value)

    @pytest.mark.parametrize("value", INVALID_CHECKDIGIT)
    def test_invalid_checkdigit_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="check digit"):
            validate_leitweg_id(value)

    def test_looks_like_true_for_pattern_match(self) -> None:
        assert looks_like_leitweg_id("04011000-12345-03") is True

    def test_looks_like_false_for_free_form(self) -> None:
        assert looks_like_leitweg_id("PO-2025-98765") is False

    def test_leitweg_id_field_on_party_accepted(
        self, minimal_invoice: ZUGFeRDInvoice
    ) -> None:
        data = minimal_invoice.buyer.model_dump()
        data["leitweg_id"] = "04011000-12345-03"
        buyer = ZUGFeRDParty.model_validate(data)
        assert buyer.leitweg_id == "04011000-12345-03"

    def test_leitweg_id_field_on_party_rejected(
        self, minimal_invoice: ZUGFeRDInvoice
    ) -> None:
        data = minimal_invoice.buyer.model_dump()
        data["leitweg_id"] = "04011000-12345-34"  # mod-97 = 32, not 1
        with pytest.raises(ValidationError, match="check digit"):
            ZUGFeRDParty.model_validate(data)
