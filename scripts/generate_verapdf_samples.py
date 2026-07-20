"""Generate sample Factur-X and XRechnung PDF/A-3 files for veraPDF CI (DE-SF-2).

Writes two PDFs to the given output directory (default: ./verapdf-samples/):
- facturx_en16931.pdf — ZUGFeRD EN_16931 profile, CII XML embedded
- xrechnung.pdf        — XRechnung profile, CII XML embedded

Usage: uv run --package mcp-einvoicing-de python scripts/generate_verapdf_samples.py [outdir]
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import (
    GermanTaxCategory,
    ZUGFeRDAddress,
    ZUGFeRDInvoice,
    ZUGFeRDParty,
    ZUGFeRDPaymentMeans,
    ZUGFeRDProfile,
    ZUGFeRDTax,
)
from mcp_einvoicing_de.serializers import ZUGFeRDCIISerializer
from mcp_einvoicing_de.utils.pdf import embed_xml_in_pdf, generate_pdf_invoice


def _base_invoice(profile: ZUGFeRDProfile, invoice_number: str) -> ZUGFeRDInvoice:
    seller = ZUGFeRDParty(
        name="Muster GmbH",
        address=ZUGFeRDAddress(line_one="Musterstr. 1", city="Berlin", postcode="10115"),
        vat_id="DE129273398",
    )
    buyer = ZUGFeRDParty(
        name="Käufer AG",
        address=ZUGFeRDAddress(line_one="Beispielweg 5", city="München", postcode="80331"),
        vat_id="DE136695976",
    )
    tax = ZUGFeRDTax(
        category=GermanTaxCategory.STANDARD,
        rate=Decimal("19"),
        taxable_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
    )
    return ZUGFeRDInvoice(
        profile=profile,
        invoice_number=invoice_number,
        invoice_date=date(2026, 7, 20),
        seller=seller,
        buyer=buyer,
        sum_of_line_net_amounts=Decimal("100.00"),
        tax_exclusive_amount=Decimal("100.00"),
        tax_inclusive_amount=Decimal("119.00"),
        tax_total=Decimal("19.00"),
        amount_due=Decimal("119.00"),
        tax_lines=[tax],
        payment_means=ZUGFeRDPaymentMeans(
            type_code="58", iban="DE89370400440532013000", bic="COBADEFFXXX"
        ),
        payment_terms="Zahlbar innerhalb von 30 Tagen netto.",
    )


def main() -> None:
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("verapdf-samples")
    outdir.mkdir(parents=True, exist_ok=True)

    facturx_invoice = _base_invoice(ZUGFeRDProfile.EN_16931, "VERAPDF-FACTURX-001")
    facturx_xml = ZUGFeRDCIISerializer().serialize(facturx_invoice, pretty_print=True)
    facturx_pdf = generate_pdf_invoice(facturx_invoice)
    facturx_hybrid = embed_xml_in_pdf(facturx_pdf, facturx_xml, profile_name="EN_16931")
    (outdir / "facturx_en16931.pdf").write_bytes(facturx_hybrid)

    xr_base = _base_invoice(ZUGFeRDProfile.XRECHNUNG, "VERAPDF-XRECHNUNG-001")
    xr_invoice = XRechnungInvoice.model_validate({
        **xr_base.model_dump(),
        "syntax": XRechnungSyntax.CII,
        "buyer_reference": "PO-VERAPDF-001",
    })
    xr_xml = ZUGFeRDCIISerializer().serialize(xr_invoice, pretty_print=True)
    xr_pdf = generate_pdf_invoice(xr_invoice)
    xr_hybrid = embed_xml_in_pdf(xr_pdf, xr_xml, profile_name="XRECHNUNG")
    (outdir / "xrechnung.pdf").write_bytes(xr_hybrid)

    print(f"Wrote {outdir / 'facturx_en16931.pdf'}")
    print(f"Wrote {outdir / 'xrechnung.pdf'}")


if __name__ == "__main__":
    main()
