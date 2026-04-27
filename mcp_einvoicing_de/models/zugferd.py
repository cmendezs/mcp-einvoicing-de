"""Pydantic models for ZUGFeRD 2.x invoices (all profiles).

Reference: https://www.ferd-net.de/standards/zugferd-2.3/index.html
Schema source: [NEED: official FeRD XSD download URL for ZUGFeRD 2.3]
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# [NEED: verify import path once mcp-einvoicing-core is published]
# from mcp_einvoicing_core.models import BaseInvoice, BaseParty, BaseTax


class ZUGFeRDProfile(str, Enum):
    """ZUGFeRD 2.x profile identifiers (URN from FeRD specification)."""

    MINIMUM = "urn:factur-x.eu:1p0:minimum"
    BASIC_WL = "urn:factur-x.eu:1p0:basicwl"
    BASIC = "urn:factur-x.eu:1p0:basic"
    EN_16931 = "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931"
    EXTENDED = "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"
    XRECHNUNG = "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.3"


class GermanTaxCategory(str, Enum):
    """EN 16931 VAT category codes relevant in Germany."""

    STANDARD = "S"  # Regelsteuersatz (19 %)
    REDUCED = "AA"  # Ermäßigter Steuersatz (7 %)
    EXEMPT = "E"  # Steuerbefreit
    REVERSE_CHARGE = "AE"  # §13b UStG (Steuerschuldnerschaft des Leistungsempfängers)
    INTRA_COMMUNITY = "K"  # Innergemeinschaftliche Lieferung (§4 Nr. 1b UStG)
    EXPORT = "G"  # Ausfuhr / Export (§4 Nr. 1a UStG)
    NOT_SUBJECT = "O"  # Nicht steuerbar
    SERVICES_OUTSIDE_SCOPE = "Z"  # Nullsteuersatz


class ZUGFeRDAddress(BaseModel):
    """Postal address — EN 16931 BG-5 / BG-8."""

    line_one: str = Field(..., description="Street and house number (BT-35 / BT-50)")
    line_two: str | None = Field(None, description="Address line 2 (BT-36 / BT-51)")
    city: str = Field(..., description="City (BT-37 / BT-52)")
    postcode: str = Field(..., description="Postcode (BT-38 / BT-53)")
    country_code: Annotated[str, Field(min_length=2, max_length=2)] = Field(
        "DE", description="ISO 3166-1 alpha-2 country code (BT-40 / BT-55)"
    )
    region: str | None = Field(None, description="Region / Bundesland (BT-39 / BT-54)")


class ZUGFeRDParty(BaseModel):
    """Trading party — covers seller (BG-4) and buyer (BG-7)."""

    name: str = Field(..., description="Legal name (BT-27 / BT-44)")
    address: ZUGFeRDAddress
    vat_id: str | None = Field(None, description="VAT number (BT-31 / BT-48), e.g. DE123456789")
    tax_number: str | None = Field(
        None, description="German Steuernummer (BT-32), e.g. 21/815/08150"
    )
    leitweg_id: str | None = Field(
        None,
        description=(
            "Leitweg-ID for public-sector buyers (BT-49). "
            "Format: <Verwaltungsebene>-<Instanzkennzeichen>-<Prüfziffer>"
        ),
    )
    electronic_address: str | None = Field(
        None, description="Peppol / EAS electronic address (BT-34 / BT-49)"
    )
    electronic_address_scheme: str | None = Field(
        None, description="EAS scheme identifier, e.g. '0088' for GLN, '0204' for Leitweg-ID"
    )
    contact_name: str | None = Field(None, description="Contact person name (BT-41)")
    contact_phone: str | None = Field(None, description="Contact phone (BT-42)")
    contact_email: str | None = Field(None, description="Contact email (BT-43)")


class ZUGFeRDTax(BaseModel):
    """VAT breakdown line — EN 16931 BG-23."""

    category: GermanTaxCategory = Field(..., description="VAT category code (BT-118)")
    rate: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"), description="Tax rate % (BT-119)")
    taxable_amount: Decimal = Field(..., description="Net taxable base amount (BT-116)")
    tax_amount: Decimal = Field(..., description="Calculated VAT amount (BT-117)")
    exemption_reason: str | None = Field(
        None, description="Exemption reason text (BT-120) — required when category ≠ S or AA"
    )
    exemption_reason_code: str | None = Field(
        None, description="VATEX exemption reason code (BT-121)"
    )

    @field_validator("tax_amount")
    @classmethod
    def validate_tax_amount(cls, v: Decimal, info: object) -> Decimal:
        # [NEED: access info.data for cross-field validation in Pydantic v2]
        return v


class ZUGFeRDAllowanceCharge(BaseModel):
    """Document-level allowance or charge — EN 16931 BG-20 / BG-21."""

    is_charge: bool = Field(..., description="True = charge, False = allowance")
    amount: Decimal = Field(..., ge=Decimal("0"), description="Amount (BT-92 / BT-99)")
    base_amount: Decimal | None = Field(None, description="Base amount (BT-93 / BT-100)")
    percentage: Decimal | None = Field(
        None, description="Percentage for calculation (BT-94 / BT-101)"
    )
    reason: str | None = Field(None, description="Reason text (BT-97 / BT-104)")
    reason_code: str | None = Field(None, description="UNCL7161 reason code (BT-98 / BT-105)")
    tax_category: GermanTaxCategory = Field(
        ..., description="VAT category of this allowance/charge (BT-95 / BT-102)"
    )
    tax_rate: Decimal = Field(
        ..., description="VAT rate of this allowance/charge (BT-96 / BT-103)"
    )


class ZUGFeRDLineItem(BaseModel):
    """Invoice line — EN 16931 BG-25. Not present in MINIMUM or BASIC WL profiles."""

    line_id: str = Field(..., description="Line identifier (BT-126)")
    name: str = Field(..., description="Item name (BT-153)")
    description: str | None = Field(None, description="Item description (BT-154)")
    quantity: Decimal = Field(..., description="Billed quantity (BT-129)")
    unit_code: str = Field(..., description="Unit of measure code — UNECE Rec 20 (BT-130)")
    unit_price: Decimal = Field(..., description="Net price per unit (BT-146)")
    unit_price_base_quantity: Decimal = Field(
        Decimal("1"), description="Base quantity for unit price (BT-149)"
    )
    line_net_amount: Decimal = Field(..., description="Line net amount (BT-131)")
    tax_category: GermanTaxCategory = Field(..., description="Line VAT category (BT-151)")
    tax_rate: Decimal = Field(..., description="Line VAT rate % (BT-152)")
    buyer_accounting_reference: str | None = Field(
        None, description="Buyer accounting reference (BT-133)"
    )
    seller_article_id: str | None = Field(None, description="Seller item identifier (BT-155)")
    buyer_article_id: str | None = Field(None, description="Buyer item identifier (BT-156)")
    standard_article_id: str | None = Field(
        None, description="Standard item identifier e.g. EAN (BT-157)"
    )
    standard_article_id_scheme: str | None = Field(
        None, description="Scheme ID for standard article identifier (BT-157-1)"
    )
    line_allowances: list[ZUGFeRDAllowanceCharge] = Field(
        default_factory=list, description="Line-level allowances and charges (BG-27 / BG-28)"
    )


class ZUGFeRDPaymentMeans(BaseModel):
    """Payment instructions — EN 16931 BG-16."""

    type_code: str = Field(
        ..., description="UNCL4461 payment means code (BT-81), e.g. '58' for SEPA Credit Transfer"
    )
    iban: str | None = Field(None, description="Payee IBAN (BT-84)")
    bic: str | None = Field(None, description="Payee BIC (BT-86)")
    account_name: str | None = Field(None, description="Account holder name (BT-85)")
    payment_id: str | None = Field(None, description="Remittance information (BT-83)")
    mandate_reference: str | None = Field(
        None, description="SEPA Direct Debit mandate reference (BT-89)"
    )
    creditor_id: str | None = Field(None, description="SEPA Creditor Identifier (BT-90)")


class ZUGFeRDInvoice(BaseModel):
    """
    Root model for a ZUGFeRD 2.x invoice.

    Covers all profiles from MINIMUM to EXTENDED.
    Fields not required by a given profile are Optional with default None.
    Profile-specific mandatory rules are enforced by the validator layer,
    not by Pydantic field-level constraints, to allow partial construction.

    Reference: EN 16931-1:2017 + FeRD ZUGFeRD 2.3 specification
    [NEED: link to official FeRD 2.3 spec PDF]
    """

    # ── Header ──────────────────────────────────────────────────────────────
    profile: ZUGFeRDProfile = Field(..., description="ZUGFeRD profile (BT-24 context parameter)")
    invoice_number: str = Field(..., description="Invoice number (BT-1)")
    invoice_date: date = Field(..., description="Invoice issue date (BT-2)")
    invoice_type_code: str = Field(
        "380", description="UNCL1001 document type code (BT-3). 380=Invoice, 381=Credit Note"
    )
    currency_code: Annotated[str, Field(min_length=3, max_length=3)] = Field(
        "EUR", description="ISO 4217 currency code (BT-5)"
    )
    buyer_reference: str | None = Field(
        None,
        description=(
            "Buyer reference / Leitweg-ID (BT-10). "
            "Mandatory for XRechnung profile and public-sector buyers."
        ),
    )
    purchase_order_reference: str | None = Field(
        None, description="Purchase order reference (BT-13)"
    )
    contract_reference: str | None = Field(None, description="Contract reference (BT-12)")
    project_reference: str | None = Field(None, description="Project reference (BT-11)")
    delivery_date: date | None = Field(None, description="Actual delivery date (BT-72)")
    billing_period_start: date | None = Field(
        None, description="Billing period start date (BT-73)"
    )
    billing_period_end: date | None = Field(None, description="Billing period end date (BT-74)")
    note: str | None = Field(None, description="Invoice note (BT-22)")

    # ── Parties ─────────────────────────────────────────────────────────────
    seller: ZUGFeRDParty = Field(..., description="Seller / Lieferant (BG-4)")
    buyer: ZUGFeRDParty = Field(..., description="Buyer / Käufer (BG-7)")

    # ── Monetary totals (BG-22) ─────────────────────────────────────────────
    sum_of_line_net_amounts: Decimal = Field(
        ..., description="Sum of invoice line net amounts (BT-106)"
    )
    allowances_total: Decimal = Field(
        Decimal("0"), description="Document-level allowances total (BT-107)"
    )
    charges_total: Decimal = Field(
        Decimal("0"), description="Document-level charges total (BT-108)"
    )
    tax_exclusive_amount: Decimal = Field(
        ..., description="Invoice total amount without VAT (BT-109)"
    )
    tax_inclusive_amount: Decimal = Field(
        ..., description="Invoice total amount with VAT (BT-112)"
    )
    tax_total: Decimal = Field(..., description="Invoice total VAT amount (BT-110)")
    amount_due: Decimal = Field(..., description="Amount due for payment (BT-115)")
    prepaid_amount: Decimal = Field(Decimal("0"), description="Prepaid amount (BT-113)")
    rounding_amount: Decimal = Field(Decimal("0"), description="Rounding amount (BT-114)")

    # ── Tax breakdown ────────────────────────────────────────────────────────
    tax_lines: list[ZUGFeRDTax] = Field(
        ..., min_length=1, description="VAT breakdown (BG-23) — at least one line required"
    )

    # ── Document-level allowances/charges ───────────────────────────────────
    allowances_charges: list[ZUGFeRDAllowanceCharge] = Field(
        default_factory=list, description="Document-level allowances and charges (BG-20 / BG-21)"
    )

    # ── Payment ─────────────────────────────────────────────────────────────
    payment_means: ZUGFeRDPaymentMeans | None = Field(
        None, description="Payment instructions (BG-16)"
    )
    payment_terms: str | None = Field(None, description="Payment terms text (BT-20)")
    due_date: date | None = Field(None, description="Payment due date (BT-9)")

    # ── Line items (absent in MINIMUM and BASIC WL) ─────────────────────────
    line_items: list[ZUGFeRDLineItem] = Field(
        default_factory=list,
        description="Invoice lines (BG-25). Required for BASIC, EN_16931, EXTENDED profiles.",
    )

    # ── Preceding invoice references ────────────────────────────────────────
    preceding_invoice_reference: str | None = Field(
        None, description="Preceding invoice reference for credit notes (BT-25)"
    )
    preceding_invoice_date: date | None = Field(
        None, description="Preceding invoice issue date (BT-26)"
    )
