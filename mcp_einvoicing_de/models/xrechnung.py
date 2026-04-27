"""Pydantic models for XRechnung 3.x invoices.

XRechnung is the German national standard derived from EN 16931.
It is mandatory for invoices addressed to German federal public authorities.
From 2025 it is also valid for B2B e-invoicing.

Reference: https://xeinkauf.de/xrechnung/
KoSIT specification: [NEED: direct URL to XRechnung 3.x specification PDF]
"""

from __future__ import annotations

from enum import Enum

from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile


class XRechnungSyntax(str, Enum):
    """XRechnung 3.x XML syntax bindings."""

    CII = "CII"  # UN/CEFACT Cross Industry Invoice (same as ZUGFeRD CII)
    UBL = "UBL"  # OASIS UBL 2.1 Invoice / Credit Note


class XRechnungInvoice(ZUGFeRDInvoice):
    """
    XRechnung 3.x invoice model.

    Extends ZUGFeRDInvoice with XRechnung-specific constraints:
    - buyer_reference (Leitweg-ID / BT-10) is MANDATORY
    - profile is fixed to ZUGFeRDProfile.XRECHNUNG
    - syntax selects CII or UBL output
    - seller vat_id OR tax_number is MANDATORY

    Additional XRechnung business rules (BR-DE-*) are enforced by the
    validator layer (validators/schematron.py), not at the model level.

    [NEED: full list of BR-DE-* rules from XRechnung 3.x spec]
    """

    syntax: XRechnungSyntax = Field(
        XRechnungSyntax.CII,
        description="XML syntax binding for XRechnung output",
    )

    model_config = {"populate_by_name": True}

    def model_post_init(self, __context: object) -> None:
        # Force profile to XRECHNUNG regardless of input
        object.__setattr__(self, "profile", ZUGFeRDProfile.XRECHNUNG)


# Avoid circular import — Field is already imported via ZUGFeRDInvoice's module
from pydantic import Field  # noqa: E402 (re-export for XRechnungInvoice annotations)
