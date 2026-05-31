"""DE-specific serializers and parsers extending mcp-einvoicing-core wire formats.

Resolved gap DE-CORE-1: wire EN16931CIISerializer, EN16931CIIParser,
EN16931UBLSerializer, and EN16931UBLParser from core into the DE package.
"""

from __future__ import annotations

from mcp_einvoicing_core.wire_formats import (
    EN16931CIIParser,
    EN16931CIISerializer,
    EN16931UBLParser,
    EN16931UBLSerializer,
)

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile


class ZUGFeRDCIISerializer(EN16931CIISerializer):
    """Serialize a ZUGFeRDInvoice to CII UN/CEFACT XML.

    ZUGFeRDInvoice is a subclass of EN16931Invoice; the base serializer handles
    all field mapping. The profile URN in the output is taken from
    ZUGFeRDInvoice.profile (a ZUGFeRDProfile enum value).
    """

    def serialize(self, invoice: ZUGFeRDInvoice, pretty_print: bool = True) -> bytes:  # type: ignore[override]
        root = self._build_root(invoice)
        return self._to_bytes(root, pretty_print=pretty_print)


class XRechnungUBLSerializer(EN16931UBLSerializer):
    """Serialize an XRechnungInvoice to UBL 2.1 XML.

    XRechnungInvoice is a subclass of EN16931Invoice. The CustomizationID
    element is populated from XRechnungInvoice.profile.
    """

    def serialize(self, invoice: XRechnungInvoice, pretty_print: bool = True) -> bytes:  # type: ignore[override]
        root = self._build_root(invoice)
        return self._to_bytes(root, pretty_print=pretty_print)


class ZUGFeRDCIIParser(EN16931CIIParser):
    """Parse CII UN/CEFACT XML into a ZUGFeRDInvoice.

    Extends the base CII parser by converting the EN16931Invoice result to
    ZUGFeRDInvoice, mapping the profile URN to a ZUGFeRDProfile enum value.
    Unknown profile URNs fall back to ZUGFeRDProfile.EN_16931.
    """

    def parse(self, xml_bytes: bytes) -> ZUGFeRDInvoice:  # type: ignore[override]
        base = super().parse(xml_bytes)
        return _to_zugferd(base)


class XRechnungUBLParser(EN16931UBLParser):
    """Parse UBL 2.1 XML into an XRechnungInvoice.

    Extends the base UBL parser by converting the EN16931Invoice result to
    XRechnungInvoice with syntax=UBL.
    """

    def parse(self, xml_bytes: bytes) -> XRechnungInvoice:  # type: ignore[override]
        base = super().parse(xml_bytes)
        data = base.model_dump()
        data["profile"] = ZUGFeRDProfile.XRECHNUNG
        data["syntax"] = XRechnungSyntax.UBL
        return XRechnungInvoice.model_validate(data)


def _to_zugferd(base: object) -> ZUGFeRDInvoice:
    """Convert an EN16931Invoice to a ZUGFeRDInvoice, mapping the profile URN."""
    data = base.model_dump()  # type: ignore[attr-defined]
    try:
        data["profile"] = ZUGFeRDProfile(base.profile)  # type: ignore[attr-defined]
    except ValueError:
        data["profile"] = ZUGFeRDProfile.EN_16931
    return ZUGFeRDInvoice.model_validate(data)
