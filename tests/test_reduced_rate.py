"""DE-SC-1: reduced-rate (7%) invoices must emit EN 16931 category S, not AA.

AA is not part of the EN 16931 / UNCL5305 category subset {S,Z,E,AE,K,G,O,L,M};
before this fix, GermanTaxCategory.REDUCED serialized as "AA" and every
reduced-rate invoice was rejected by Schematron at ZRE / OZG-RE.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from decimal import Decimal

import pytest
from lxml import etree

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import (
    GermanTaxCategory,
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDLineItem,
    ZUGFeRDParty,
    ZUGFeRDProfile,
    ZUGFeRDTax,
)
from mcp_einvoicing_de.serializers import (
    XRechnungUBLSerializer,
    ZUGFeRDCIISerializer,
)
from mcp_einvoicing_de.validators.schematron import SchematronValidator

_SAXON_AVAILABLE = importlib.util.find_spec("saxonche") is not None

_RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"


def test_reduced_category_aliases_standard() -> None:
    """GermanTaxCategory.REDUCED must bind to EN 16931 category "S"."""
    assert GermanTaxCategory.REDUCED.value == "S"
    assert GermanTaxCategory.REDUCED is GermanTaxCategory.STANDARD


def _make_reduced_rate_invoice() -> ZUGFeRDInvoice:
    seller = ZUGFeRDParty(
        name="Buchhandlung Muster GmbH",
        address=ZUGFeRDAddress(line_one="Musterstr. 1", city="Berlin", postcode="10115"),
        vat_id="DE129273398",
    )
    buyer = ZUGFeRDParty(
        name="Käufer AG",
        address=ZUGFeRDAddress(line_one="Beispielweg 5", city="München", postcode="80331"),
        vat_id="DE136695976",
    )
    tax = ZUGFeRDTax(
        category=GermanTaxCategory.REDUCED,
        rate=Decimal("7"),
        taxable_amount=Decimal("100.00"),
        tax_amount=Decimal("7.00"),
    )
    line = ZUGFeRDLineItem(
        line_id="1",
        name="Buch: Python fuer Anfaenger",
        quantity=Decimal("1"),
        unit_code="C62",
        unit_price=Decimal("100.00"),
        net_amount=Decimal("100.00"),
        line_net_amount=Decimal("100.00"),
        tax_rate=Decimal("7"),
        tax_category=GermanTaxCategory.REDUCED,
    )
    return ZUGFeRDInvoice(
        profile=ZUGFeRDProfile.EN_16931,
        invoice_number="RE-2026-REDUCED-001",
        invoice_date=date(2026, 7, 19),
        seller=seller,
        buyer=buyer,
        sum_of_line_net_amounts=Decimal("100.00"),
        tax_exclusive_amount=Decimal("100.00"),
        tax_inclusive_amount=Decimal("107.00"),
        tax_total=Decimal("7.00"),
        amount_due=Decimal("107.00"),
        tax_lines=[tax],
        line_items=[line],
        payment_terms="Zahlbar innerhalb von 30 Tagen netto.",
    )


class TestReducedRateCII:
    def test_category_code_emitted_as_s(self) -> None:
        invoice = _make_reduced_rate_invoice()
        xml_bytes = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=True)
        root = etree.fromstring(xml_bytes)
        category_codes = root.xpath(
            "//ram:ApplicableTradeTax/ram:CategoryCode/text()",
            namespaces={"ram": _RAM},
        )
        assert category_codes, "Expected at least one ram:CategoryCode element"
        assert all(code == "S" for code in category_codes)

    @pytest.mark.skipif(not _SAXON_AVAILABLE, reason="saxonche extra not installed")
    def test_schematron_runs_without_category_error(self) -> None:
        """Assert Schematron never fires a category-code business rule for "S".

        `errors == []` cannot be asserted here: this fixture is intentionally
        minimal and still trips two unrelated findings (BR-FX-EN-04 missing
        delivery date/invoicing period, and an `ram:ID` format check) that
        have nothing to do with the tax category. This test guards
        specifically against category-code (BR-S-*, BR-CO-* "CategoryCode")
        findings, which is what DE-SC-1 fixed.
        """
        invoice = _make_reduced_rate_invoice()
        xml_bytes = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=True)
        validator = SchematronValidator("en16931_cii")
        result = validator.validate(xml_bytes, profile="EN_16931", syntax="CII")
        category_errors = [e for e in result.errors if "categor" in e.text.lower()]
        assert category_errors == [], f"Category-code errors: {category_errors}"


class TestReducedRateUBL:
    def _make_ubl_invoice(self) -> XRechnungInvoice:
        base = _make_reduced_rate_invoice()
        return XRechnungInvoice.model_validate({
            **base.model_dump(),
            "syntax": XRechnungSyntax.UBL,
            "buyer_reference": "PO-2026-0042",
        })

    def test_category_id_emitted_as_s(self) -> None:
        invoice = self._make_ubl_invoice()
        xml_bytes = XRechnungUBLSerializer().serialize(invoice, pretty_print=True)
        root = etree.fromstring(xml_bytes)
        category_ids = root.xpath(
            "//cac:ClassifiedTaxCategory/cbc:ID/text()",
            namespaces={
                "cbc": _CBC,
                "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            },
        )
        assert category_ids, "Expected at least one cbc:ID under ClassifiedTaxCategory"
        assert all(code == "S" for code in category_ids)

    @pytest.mark.skipif(not _SAXON_AVAILABLE, reason="saxonche extra not installed")
    def test_schematron_runs_without_category_error(self) -> None:
        """Assert neither the EN 16931 base nor the XRechnung CIUS ruleset
        raises a category-code business rule for the reduced-rate "S" category.

        The fixture is not a fully Peppol/XRechnung-compliant invoice (it is
        missing BG-16 payment instructions, electronic addresses, and seller
        contact, which are unrelated to DE-SC-1); those CIUS findings are
        expected and out of scope here. This test only guards against
        category-code regressions recurring in either stylesheet.
        """
        invoice = self._make_ubl_invoice()
        xml_bytes = XRechnungUBLSerializer().serialize(invoice, pretty_print=True)

        for key in ("en16931_ubl", "xrechnung_ubl"):
            result = SchematronValidator(key).validate(
                xml_bytes, profile="XRECHNUNG", syntax="UBL"
            )
            category_errors = [e for e in result.errors if "categor" in e.text.lower()]
            assert category_errors == [], f"{key} category-code errors: {category_errors}"
