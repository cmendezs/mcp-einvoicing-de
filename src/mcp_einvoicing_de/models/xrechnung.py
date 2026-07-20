"""Pydantic models for XRechnung 3.x invoices.

XRechnung is the German national standard derived from EN 16931.
It is mandatory for invoices addressed to German federal public authorities.
From 2025 it is also valid for B2B e-invoicing.

Reference: https://xeinkauf.de/xrechnung/
KoSIT specification: [NEED: direct URL to XRechnung 3.x specification PDF]
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile


class XRechnungSyntax(StrEnum):
    """XRechnung 3.x XML syntax bindings."""

    CII = "CII"  # UN/CEFACT Cross Industry Invoice (same as ZUGFeRD CII)
    UBL = "UBL"  # OASIS UBL 2.1 Invoice / Credit Note


class XRechnungInvoice(ZUGFeRDInvoice):
    """
    XRechnung 3.x invoice model.

    Extends ZUGFeRDInvoice with XRechnung-specific constraints:
    - buyer_reference (Leitweg-ID / BT-10) is MANDATORY
    - profile defaults to ZUGFeRDProfile.XRECHNUNG
    - syntax selects CII or UBL output
    - seller vat_id OR tax_number is MANDATORY

    Additional XRechnung business rules (BR-DE-*) are enforced by the
    validator layer (validators/schematron.py), not at the model level.

    [NEED: full list of BR-DE-* rules from XRechnung 3.x spec]
    """

    profile: ZUGFeRDProfile = Field(  # type: ignore[assignment]
        ZUGFeRDProfile.XRECHNUNG,
        description="XRechnung profile URN (BT-24) — always XRECHNUNG",
    )
    syntax: XRechnungSyntax = Field(
        XRechnungSyntax.CII,
        description="XML syntax binding for XRechnung output",
    )
    # BR-DE-15: Buyer reference (BT-10) is mandatory for XRechnung.
    # EN16931Invoice declares this Optional[str] = None; we override it as
    # required here so Pydantic enforces the rule at construction time.
    buyer_reference: str = Field(  # type: ignore[assignment]
        ...,
        description=(
            "Leitweg-ID or buyer-assigned routing reference (BT-10). "
            "Mandatory for all XRechnung invoices (BR-DE-15)."
        ),
    )

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_buyer_reference_leitweg(self) -> XRechnungInvoice:
        """Validate Leitweg-ID check digit only in a B2G context (DE-SF-3).

        XRechnung buyer_reference may be a Leitweg-ID (B2G, mandatory
        check-digit format) or a free-form buyer reference string (B2B
        purchase order number, etc.). Gating on ``buyer.leitweg_id is not
        None`` — rather than on whether buyer_reference merely *looks like* a
        Leitweg-ID — avoids false-matching a B2B PO number that happens to
        share the Leitweg-ID shape (e.g. "04011000-12345-67") and rejecting a
        legitimate invoice over a check digit that was never meant to apply.
        """
        from mcp_einvoicing_de.utils.leitweg import validate_leitweg_id  # noqa: PLC0415

        if self.buyer.leitweg_id is not None:
            validate_leitweg_id(self.buyer_reference)
        return self

    def model_post_init(self, __context: object) -> None:
        # Enforce XRECHNUNG regardless of any caller-supplied profile value.
        object.__setattr__(self, "profile", ZUGFeRDProfile.XRECHNUNG)

