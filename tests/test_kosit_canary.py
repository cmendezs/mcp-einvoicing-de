"""DE-V1-2: KoSIT cloud canary corpus.

Replays a curated set of invoices against https://validator.kosit.de and
asserts they all validate successfully. Gated behind EINVOICING_DE_INTEGRATION_TESTS=1.
Runs nightly in CI via .github/workflows/kosit-canary.yml.
"""

from __future__ import annotations

import os
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
from mcp_einvoicing_de.serializers import ZUGFeRDCIISerializer
from mcp_einvoicing_de.validators.kosit import KoSITValidator

_INTEGRATION = os.environ.get("EINVOICING_DE_INTEGRATION_TESTS") == "1"
pytestmark = pytest.mark.skipif(not _INTEGRATION, reason="Integration tests disabled")


def _canary_invoice(
    profile: ZUGFeRDProfile,
    invoice_number: str,
    with_lines: bool = True,
) -> bytes:
    seller = ZUGFeRDParty(
        name="Canary Verkäufer GmbH",
        address=ZUGFeRDAddress(
            line_one="Teststraße 42", city="Berlin", postcode="10115", country_code="DE"
        ),
        vat_id="DE129273398",
    )
    buyer = ZUGFeRDParty(
        name="Canary Käufer AG",
        address=ZUGFeRDAddress(
            line_one="Prüfweg 7", city="München", postcode="80331", country_code="DE"
        ),
        vat_id="DE136695976",
    )
    tax = ZUGFeRDTax(
        category=GermanTaxCategory.STANDARD,
        rate=Decimal("19"),
        taxable_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
    )
    lines = []
    if with_lines:
        lines = [
            ZUGFeRDLineItem(
                line_id="1",
                name="Canary item",
                quantity=Decimal("1"),
                unit_code="C62",
                unit_price=Decimal("100.00"),
                line_net_amount=Decimal("100.00"),
                tax_category=GermanTaxCategory.STANDARD,
                tax_rate=Decimal("19"),
            ),
        ]
    invoice = ZUGFeRDInvoice(
        profile=profile,
        invoice_number=invoice_number,
        invoice_date=date(2025, 6, 1),
        seller=seller,
        buyer=buyer,
        sum_of_line_net_amounts=Decimal("100.00"),
        tax_exclusive_amount=Decimal("100.00"),
        tax_inclusive_amount=Decimal("119.00"),
        tax_total=Decimal("19.00"),
        amount_due=Decimal("119.00"),
        tax_lines=[tax],
        line_items=lines,
        payment_means=ZUGFeRDPaymentMeans(type_code="58", iban="DE89370400440532013000"),
        buyer_reference=f"CANARY-{invoice_number}",
    )
    return ZUGFeRDCIISerializer().serialize(invoice, pretty_print=True)


_CANARY_SET: list[tuple[ZUGFeRDProfile, str, bool]] = [
    (ZUGFeRDProfile.MINIMUM, "CANARY-MIN-001", False),
    (ZUGFeRDProfile.BASIC_WL, "CANARY-BWL-001", False),
    (ZUGFeRDProfile.BASIC, "CANARY-BAS-001", True),
    (ZUGFeRDProfile.EN_16931, "CANARY-EN-001", True),
    (ZUGFeRDProfile.EXTENDED, "CANARY-EXT-001", True),
    (ZUGFeRDProfile.XRECHNUNG, "CANARY-XR-001", True),
]


class TestKoSITCanary:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("profile,inv_num,with_lines", _CANARY_SET)
    async def test_canary_validates(
        self,
        profile: ZUGFeRDProfile,
        inv_num: str,
        with_lines: bool,
    ) -> None:
        xml_bytes = _canary_invoice(profile, inv_num, with_lines)
        validator = KoSITValidator(KoSITValidator._UNVERIFIED_DEFAULT_KOSIT_URL)
        result = await validator.validate(xml_bytes, filename=f"{inv_num}.xml")

        assert result.is_valid, (
            f"KoSIT validation failed for {inv_num} ({profile.name}): "
            f"{[e.text for e in result.errors]}"
        )
