"""MCP tool: invoice_convert — convert between ZUGFeRD profiles and to / from XRechnung.

Supports:

- ZUGFeRD profile upgrade/downgrade in CII syntax (line items removed for MINIMUM / BASIC_WL;
  requires allow_data_loss=True)
- ZUGFeRD EN_16931 / EXTENDED ↔ XRechnung in CII syntax (URN swap)
- XRechnung UBL → XRechnung UBL profile URN swap
- Cross-syntax CII ↔ UBL transformation via core convert_wire_format (v0.4.0)
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_einvoicing_core.convert import Syntax, convert_wire_format
from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.xml_utils import format_error, resolve_xml_input
from pydantic import BaseModel, Field

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import ZUGFeRDProfile
from mcp_einvoicing_de.serializers import (
    XRechnungUBLParser,
    XRechnungUBLSerializer,
    ZUGFeRDCIIParser,
    ZUGFeRDCIISerializer,
)
from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile

logger = logging.getLogger(__name__)

# Ordering used to detect downgrades. Index 0 is the most reduced profile.
_PROFILE_ORDER: tuple[ZUGFeRDProfile, ...] = (
    ZUGFeRDProfile.MINIMUM,
    ZUGFeRDProfile.BASIC_WL,
    ZUGFeRDProfile.BASIC,
    ZUGFeRDProfile.EN_16931,
    ZUGFeRDProfile.EXTENDED,
)

# Profiles that omit invoice lines per EN 16931 / FeRD.
_LINE_FREE_PROFILES: frozenset[ZUGFeRDProfile] = frozenset(
    {ZUGFeRDProfile.MINIMUM, ZUGFeRDProfile.BASIC_WL}
)


class InvoiceConvertOutput(BaseModel):
    """Output schema for invoice_convert."""

    xml_content: str | None = None
    source_profile: str
    source_syntax: str
    target_profile: str
    target_syntax: str
    data_loss_warnings: list[str] = Field(
        default_factory=list,
        description="Fields discarded during profile downgrade.",
    )
    conversion_notes: list[str] = Field(default_factory=list)


def _resolve_target_profile(name: str) -> ZUGFeRDProfile:
    return ZUGFeRDProfile[name.upper()]


def _is_downgrade(source: ZUGFeRDProfile, target: ZUGFeRDProfile) -> bool:
    if source not in _PROFILE_ORDER or target not in _PROFILE_ORDER:
        return False
    return _PROFILE_ORDER.index(target) < _PROFILE_ORDER.index(source)


async def invoice_convert(
    target_profile: str,
    xml_content: str | None = None,
    xml_base64: str | None = None,
    target_syntax: str = "CII",
    allow_data_loss: bool = False,
) -> dict[str, Any]:
    """Convert a ZUGFeRD or XRechnung invoice to a different profile or syntax.

    Supports ZUGFeRD profile upgrades and downgrades, ZUGFeRD <-> XRechnung
    conversion, and cross-syntax CII <-> UBL transformation. Profile
    downgrades may result in data loss; set allow_data_loss=True to permit
    this.

    Args:
        target_profile: One of: MINIMUM, BASIC_WL, BASIC, EN_16931,
            EXTENDED, XRECHNUNG.
        xml_content: Raw XML string of the source invoice.
        xml_base64: Base64-encoded XML bytes.
        target_syntax: Target syntax: 'CII' or 'UBL'. UBL is only valid for
            XRECHNUNG.
        allow_data_loss: If True, allow profile downgrades that discard
            data. Discarded fields are listed in the output. If False and
            data loss would occur, the conversion is rejected.
    """
    try:
        xml_bytes = resolve_xml_input(xml_content, xml_base64)
    except (ValueError, EInvoicingError) as exc:
        return format_error(str(exc))

    try:
        source_syntax = detect_invoice_syntax(xml_bytes)
    except ValueError as exc:
        return format_error(str(exc))

    source_profile = detect_zugferd_profile(xml_bytes)
    if source_profile is None:
        return format_error(
            "Could not detect source profile from GuidelineID / CustomizationID. "
            "Provide a ZUGFeRD or XRechnung invoice with a recognised profile URN."
        )

    try:
        target_profile_enum = _resolve_target_profile(target_profile)
    except KeyError as exc:
        return format_error(f"Unknown target_profile: {exc}")

    try:
        target_syntax_enum = XRechnungSyntax(target_syntax.upper())
    except ValueError as exc:
        return format_error(f"Unknown target_syntax: {exc}")

    if (
        target_syntax_enum == XRechnungSyntax.UBL
        and target_profile_enum != ZUGFeRDProfile.XRECHNUNG
    ):
        return format_error(
            "UBL syntax is only defined for the XRECHNUNG profile. "
            "Use target_syntax='CII' for ZUGFeRD profiles."
        )

    # Cross-syntax conversion: delegate to core convert_wire_format, then
    # parse the result with the DE parser so DE-specific extensions are preserved.
    if source_syntax.value != target_syntax_enum.value:
        try:
            converted_bytes = convert_wire_format(
                xml_bytes, target=Syntax(target_syntax_enum.value)
            )
        except Exception as exc:
            return format_error(f"Cross-syntax conversion failed: {exc}")
        xml_bytes = converted_bytes
        source_syntax = target_syntax_enum

    # Parse the source invoice into the typed model.
    notes: list[str] = []
    data_loss: list[str] = []
    try:
        if source_syntax == XRechnungSyntax.CII:
            invoice = ZUGFeRDCIIParser().parse(xml_bytes)
        else:
            invoice = XRechnungUBLParser().parse(xml_bytes)
    except Exception as exc:
        return format_error(f"Parse failed: {exc}")

    # Detect downgrade and handle line-free target profiles.
    downgrade = _is_downgrade(source_profile, target_profile_enum)
    if downgrade:
        if target_profile_enum in _LINE_FREE_PROFILES and invoice.line_items:
            if not allow_data_loss:
                return format_error(
                    f"Downgrade to {target_profile_enum.name} would drop "
                    f"{len(invoice.line_items)} line item(s). Re-run with "
                    "allow_data_loss=True to permit this."
                )
            data_loss.append(
                f"Dropped {len(invoice.line_items)} line item(s); {target_profile_enum.name} "
                "omits BG-25 invoice lines per FeRD profile rules."
            )
            invoice.line_items = []
        notes.append(
            f"Profile downgrade {source_profile.name} -> {target_profile_enum.name}. Document-level "
            "totals are preserved unchanged."
        )
    elif source_profile != target_profile_enum:
        notes.append(
            f"Profile change {source_profile.name} -> {target_profile_enum.name}. The GuidelineID "
            "URN is rewritten; no field pruning was needed."
        )

    # Rewrite the profile URN. The XRechnung syntax flag is also kept in sync.
    invoice.profile = target_profile_enum
    if isinstance(invoice, XRechnungInvoice):
        invoice.syntax = target_syntax_enum
    elif target_profile_enum == ZUGFeRDProfile.XRECHNUNG:
        # Convert ZUGFeRDInvoice to XRechnungInvoice when the target is XRechnung so that
        # the XRechnung serializer can pick up the CustomizationID URN.
        invoice = XRechnungInvoice.model_validate(
            {**invoice.model_dump(), "syntax": target_syntax_enum}
        )

    # Re-serialize in the target syntax.
    try:
        if target_syntax_enum == XRechnungSyntax.UBL:
            assert isinstance(invoice, XRechnungInvoice)
            xml_out = XRechnungUBLSerializer().serialize(invoice, pretty_print=True)
        else:
            xml_out = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=True)
    except Exception as exc:
        return format_error(f"Serialise failed: {exc}")

    output = InvoiceConvertOutput(
        xml_content=xml_out.decode("utf-8"),
        source_profile=source_profile.name,
        source_syntax=source_syntax.value,
        target_profile=target_profile_enum.name,
        target_syntax=target_syntax_enum.value,
        data_loss_warnings=data_loss,
        conversion_notes=notes,
    )
    return output.model_dump()
