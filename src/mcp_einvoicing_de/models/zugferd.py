"""Pydantic models for ZUGFeRD 2.x invoices (all profiles).

Reference: https://www.ferd-net.de/standards/zugferd-2.3/index.html
Schema source: [NEED: official FeRD XSD download URL for ZUGFeRD 2.3]
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from mcp_einvoicing_core import TaxIdentifier
from mcp_einvoicing_core.en16931 import (
    EN16931Address,
    EN16931AllowanceCharge,
    EN16931Invoice,
    EN16931LineItem,
    EN16931Party,
    EN16931PaymentMeans,
    EN16931Tax,
)
from pydantic import Field, field_validator


class ZUGFeRDProfile(StrEnum):
    """ZUGFeRD 2.x profile identifiers (URN from FeRD specification)."""

    MINIMUM = "urn:factur-x.eu:1p0:minimum"
    BASIC_WL = "urn:factur-x.eu:1p0:basicwl"
    BASIC = "urn:factur-x.eu:1p0:basic"
    EN_16931 = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931"
    EXTENDED = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"
    XRECHNUNG = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"


class GermanTaxCategory(StrEnum):
    """EN 16931 VAT category codes relevant in Germany."""

    STANDARD = "S"  # Regelsteuersatz (19 %)
    REDUCED = "AA"  # Ermäßigter Steuersatz (7 %)
    EXEMPT = "E"  # Steuerbefreit
    REVERSE_CHARGE = "AE"  # §13b UStG (Steuerschuldnerschaft des Leistungsempfängers)
    INTRA_COMMUNITY = "K"  # Innergemeinschaftliche Lieferung (§4 Nr. 1b UStG)
    EXPORT = "G"  # Ausfuhr / Export (§4 Nr. 1a UStG)
    NOT_SUBJECT = "O"  # Nicht steuerbar
    SERVICES_OUTSIDE_SCOPE = "Z"  # Nullsteuersatz


class ZUGFeRDAddress(EN16931Address):
    """Postal address — EN 16931 BG-5 / BG-8."""

    country_code: Annotated[str, Field(min_length=2, max_length=2)] = Field(  # type: ignore[assignment]
        "DE", description="ISO 3166-1 alpha-2 country code (BT-40 / BT-55)"
    )


class ZUGFeRDParty(EN16931Party):
    """Trading party — covers seller (BG-4) and buyer (BG-7)."""

    address: ZUGFeRDAddress  # type: ignore[assignment]
    tax_number: str | None = Field(
        None, description="German Steuernummer (BT-32), e.g. 21/815/08150"
    )
    leitweg_id: str | None = Field(
        None,
        description=(
            "Leitweg-ID for public-sector buyers (BT-49). "
            "Format: <Verwaltungsebene>[-<Instanzkennzeichen>]-<Prüfziffer>"
        ),
    )

    @field_validator("leitweg_id", mode="after")
    @classmethod
    def validate_leitweg_id_field(cls, v: str | None) -> str | None:
        if v is not None:
            # Deferred import avoids circular: zugferd → utils.leitweg →
            # utils/__init__ → utils.xml_utils → models.xrechnung → zugferd
            from mcp_einvoicing_de.utils.leitweg import validate_leitweg_id  # noqa: PLC0415

            validate_leitweg_id(v)
        return v

    @field_validator("vat_id", mode="after")
    @classmethod
    def _validate_de_vat_id_checksum(cls, v: str | None) -> str | None:
        """Enforce the German USt-IdNr DIN 4774 mod-11 check digit (BT-31 / BT-48).

        Scoped to DE-prefixed values only: non-DE counterparty VATs (FR, IT, etc.)
        used for cross-border B2B invoicing are pass-through, since their format
        rules belong to the issuing country's validator. Delegates to the core
        3-layer pattern: TaxIdentifier.validate_de_vat (Layer 1).
        """
        if v is None or not v.upper().startswith("DE"):
            return v
        ok, error = TaxIdentifier.validate_de_vat(v)
        if not ok:
            raise ValueError(f"Invalid German USt-IdNr (BT-31 / BT-48): {error}")
        return v


class ZUGFeRDTax(EN16931Tax):
    """VAT breakdown line — EN 16931 BG-23."""

    category: GermanTaxCategory = Field(  # type: ignore[assignment]
        ..., description="VAT category code (BT-118)"
    )

    @field_validator("tax_amount")
    @classmethod
    def validate_tax_amount(cls, v: Decimal, info: object) -> Decimal:
        # [NEED: access info.data for cross-field validation in Pydantic v2]
        return v


class ZUGFeRDAllowanceCharge(EN16931AllowanceCharge):
    """Document-level allowance or charge — EN 16931 BG-20 / BG-21."""

    tax_category: GermanTaxCategory = Field(  # type: ignore[assignment]
        ..., description="VAT category of this allowance/charge (BT-95 / BT-102)"
    )


class ZUGFeRDLineItem(EN16931LineItem):
    """Invoice line — EN 16931 BG-25. Not present in MINIMUM or BASIC WL profiles."""

    tax_category: GermanTaxCategory = Field(  # type: ignore[assignment]
        ..., description="Line VAT category (BT-151)"
    )
    line_allowances: list[ZUGFeRDAllowanceCharge] = Field(  # type: ignore[assignment]
        default_factory=list, description="Line-level allowances and charges (BG-27 / BG-28)"
    )


class ZUGFeRDPaymentMeans(EN16931PaymentMeans):
    """Payment instructions — EN 16931 BG-16."""


class ZUGFeRDInvoice(EN16931Invoice):
    """Root model for a ZUGFeRD 2.x invoice.

    Covers all profiles from MINIMUM to EXTENDED.
    Fields not required by a given profile are Optional with default None.
    Profile-specific mandatory rules are enforced by the validator layer,
    not by Pydantic field-level constraints, to allow partial construction.

    Reference: EN 16931-1:2017 + FeRD ZUGFeRD 2.3 specification
    [NEED: link to official FeRD 2.3 spec PDF]
    """

    _allowed_profiles: frozenset[str] = frozenset(  # type: ignore[assignment]
        {e.value for e in ZUGFeRDProfile}
    )

    profile: ZUGFeRDProfile = Field(  # type: ignore[assignment]
        ..., description="ZUGFeRD profile (BT-24 context parameter)"
    )
    seller: ZUGFeRDParty = Field(..., description="Seller / Lieferant (BG-4)")  # type: ignore[assignment]
    buyer: ZUGFeRDParty = Field(..., description="Buyer / Käufer (BG-7)")  # type: ignore[assignment]
    tax_lines: list[ZUGFeRDTax] = Field(  # type: ignore[assignment]
        ..., description="VAT breakdown (BG-23) — at least one line required"
    )
    allowances_charges: list[ZUGFeRDAllowanceCharge] = Field(  # type: ignore[assignment]
        default_factory=list,
        description="Document-level allowances and charges (BG-20 / BG-21)",
    )
    payment_means: ZUGFeRDPaymentMeans | None = Field(  # type: ignore[assignment]
        None, description="Payment instructions (BG-16)"
    )
    line_items: list[ZUGFeRDLineItem] = Field(  # type: ignore[assignment]
        default_factory=list,
        description="Invoice lines (BG-25). Required for BASIC, EN_16931, EXTENDED profiles.",
    )
    tax_representative: ZUGFeRDParty | None = Field(
        None,
        description=(
            "Seller tax representative (BG-11). Mandatory when a non-resident seller "
            "appoints a German fiscal representative under §22a UStG. When present, the "
            "representative's VAT identifier (BT-63) is required by EN 16931 BR-18."
        ),
    )


# ---------------------------------------------------------------------------
# Register ZUGFeRD / XRechnung profiles in the core ProfileRegistry.
# Imported by any DE tool that needs to look up GuidelineID URNs or validate
# conversion paths without hard-coding the values.
# ---------------------------------------------------------------------------

from mcp_einvoicing_core.profile_registry import profile_registry as _registry  # noqa: E402

_registry.register("DE", "MINIMUM",   "CII", ZUGFeRDProfile.MINIMUM.value)
_registry.register("DE", "BASIC_WL",  "CII", ZUGFeRDProfile.BASIC_WL.value)
_registry.register("DE", "BASIC",     "CII", ZUGFeRDProfile.BASIC.value)
_registry.register("DE", "EN_16931",  "CII", ZUGFeRDProfile.EN_16931.value)
_registry.register("DE", "EN_16931",  "UBL", ZUGFeRDProfile.EN_16931.value)
_registry.register("DE", "EXTENDED",  "CII", ZUGFeRDProfile.EXTENDED.value)
_registry.register("DE", "XRECHNUNG", "CII", ZUGFeRDProfile.XRECHNUNG.value)
_registry.register("DE", "XRECHNUNG", "UBL", ZUGFeRDProfile.XRECHNUNG.value)
