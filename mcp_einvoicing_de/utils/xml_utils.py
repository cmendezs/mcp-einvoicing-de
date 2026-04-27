"""XML inspection helpers for ZUGFeRD and XRechnung documents."""

from __future__ import annotations

from lxml import etree

from mcp_einvoicing_de.models.zugferd import ZUGFeRDProfile
from mcp_einvoicing_de.models.xrechnung import XRechnungSyntax

# Namespace maps for CII and UBL
_NS_CII_RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
_NS_UBL_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
_NS_UBL_CREDIT_NOTE = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"

# ZUGFeRD profile GuidelineSpecifiedDocumentContextParameter URNs
_PROFILE_URN_MAP: dict[str, ZUGFeRDProfile] = {p.value: p for p in ZUGFeRDProfile}


def detect_invoice_syntax(xml_bytes: bytes) -> XRechnungSyntax:
    """Detect whether *xml_bytes* uses CII or UBL syntax."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    ns = root.nsmap.get(None) or root.nsmap.get("")
    tag_ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""

    if tag_ns in (_NS_UBL_INVOICE, _NS_UBL_CREDIT_NOTE):
        return XRechnungSyntax.UBL
    if tag_ns == _NS_CII_RSM or "CrossIndustryInvoice" in root.tag:
        return XRechnungSyntax.CII
    if ns in (_NS_UBL_INVOICE, _NS_UBL_CREDIT_NOTE):
        return XRechnungSyntax.UBL

    raise ValueError(
        f"Cannot determine invoice syntax from root element {root.tag!r}. "
        "Expected CII (CrossIndustryInvoice) or UBL (Invoice / CreditNote)."
    )


def detect_zugferd_profile(xml_bytes: bytes) -> ZUGFeRDProfile | None:
    """
    Extract the ZUGFeRD / XRechnung profile URN from the GuidelineID element.

    Returns None if no recognised profile URN is found.
    CII path: //rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID
    UBL path: //cbc:CustomizationID
    [NEED: confirm exact XPath for UBL profile ID in XRechnung UBL]
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return None

    ns_ram = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    ns_rsm = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    ns_cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    # Try CII
    cii_xpath = (
        f"{{{ns_rsm}}}ExchangedDocumentContext"
        f"/{{{ns_ram}}}GuidelineSpecifiedDocumentContextParameter"
        f"/{{{ns_ram}}}ID"
    )
    el = root.find(cii_xpath)
    if el is not None and el.text:
        return _PROFILE_URN_MAP.get(el.text.strip())

    # Try UBL
    ubl_customization = root.find(f"{{{ns_cbc}}}CustomizationID")
    if ubl_customization is not None and ubl_customization.text:
        return _PROFILE_URN_MAP.get(ubl_customization.text.strip())

    return None
