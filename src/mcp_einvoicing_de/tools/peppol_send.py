"""MCP tool: peppol_send — deliver a ZUGFeRD invoice via Peppol AS4.

Transmits a ZUGFeRDInvoice to a German Peppol-registered participant via AS4,
consuming the core PeppolTransmitter primitives (core v1.9.0). The invoice is
serialized to UBL (Peppol BIS 3.0 is UBL-only) using XRechnungUBLSerializer
before transmission.

Credentials are supplied via environment variables:
  EINVOICING_DE_PEPPOL_CERT_PATH — path to PEM signing certificate
  EINVOICING_DE_PEPPOL_KEY_PATH  — path to PEM private key
  EINVOICING_DE_PEPPOL_KEY_PASSWORD — optional private key password
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import mcp.types as types
from mcp_einvoicing_core.exceptions import EInvoicingError, PlatformError
from mcp_einvoicing_core.peppol import PeppolEnvironment, PeppolParticipantId
from mcp_einvoicing_core.peppol.transport import AS4Credentials, PeppolTransmitter
from mcp_einvoicing_core.xml_utils import format_error
from pydantic import BaseModel, Field

from mcp_einvoicing_de.models.xrechnung import XRechnungInvoice, XRechnungSyntax
from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice, ZUGFeRDProfile
from mcp_einvoicing_de.serializers import XRechnungUBLSerializer

logger = logging.getLogger(__name__)


class PeppolSendInput(BaseModel):
    """Input schema for peppol_send."""

    invoice: dict[str, Any] = Field(
        ..., description="ZUGFeRDInvoice data to transmit."
    )
    recipient_id: str = Field(
        ...,
        description=(
            "Peppol participant identifier of the receiver in 'scheme:value' format, "
            "e.g. '0204:991-1234512345-06' (Leitweg-ID) or '9930:DE123456789' (DE VAT)."
        ),
    )
    sender_id: str = Field(
        ...,
        description="Peppol AP identifier of the sender, e.g. 'POP000001'.",
    )
    environment: str = Field(
        "test",
        description="Peppol environment: 'production' or 'test'.",
    )


class PeppolSendOutput(BaseModel):
    """Output schema for peppol_send."""

    message_id: str = Field(..., description="AS4 message ID of the sent UserMessage.")
    receipt_message_id: str = Field(..., description="AS4 receipt signal message ID.")
    recipient_id: str
    status: str = Field("delivered", description="Transmission status.")


TOOL_PEPPOL_SEND = types.Tool(
    name="peppol_send",
    description=(
        "Send a ZUGFeRD invoice to a German Peppol participant via AS4. "
        "The invoice is serialized to UBL (Peppol BIS 3.0) and transmitted "
        "using the core PeppolTransmitter. Requires signing credentials "
        "configured via EINVOICING_DE_PEPPOL_CERT_PATH and "
        "EINVOICING_DE_PEPPOL_KEY_PATH environment variables."
    ),
    inputSchema={
        "type": "object",
        "required": ["invoice", "recipient_id", "sender_id"],
        "properties": {
            "invoice": {"type": "object", "description": "ZUGFeRDInvoice data."},
            "recipient_id": {
                "type": "string",
                "description": "Peppol participant ID (scheme:value).",
            },
            "sender_id": {
                "type": "string",
                "description": "Sender AP identifier.",
            },
            "environment": {
                "type": "string",
                "enum": ["production", "test"],
                "default": "test",
            },
        },
    },
)


def _load_credentials() -> AS4Credentials:
    cert_path = os.environ.get("EINVOICING_DE_PEPPOL_CERT_PATH")
    key_path = os.environ.get("EINVOICING_DE_PEPPOL_KEY_PATH")
    key_password = os.environ.get("EINVOICING_DE_PEPPOL_KEY_PASSWORD")

    if not cert_path or not key_path:
        raise PlatformError(
            status_code=0,
            message=(
                "Peppol signing credentials not configured. Set "
                "EINVOICING_DE_PEPPOL_CERT_PATH and EINVOICING_DE_PEPPOL_KEY_PATH "
                "environment variables."
            ),
        )

    return AS4Credentials(
        certificate_path=cert_path,
        private_key_path=key_path,
        private_key_password=key_password,
    )


async def handle_peppol_send(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for peppol_send."""
    try:
        params = PeppolSendInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        invoice = ZUGFeRDInvoice.model_validate(params.invoice)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(f"Invalid invoice: {exc}")))]

    try:
        recipient = PeppolParticipantId.parse(params.recipient_id)
    except ValueError as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        credentials = _load_credentials()
    except PlatformError as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(exc.message)))]

    env = (
        PeppolEnvironment.PRODUCTION
        if params.environment == "production"
        else PeppolEnvironment.TEST
    )

    xrechnung = XRechnungInvoice.model_validate({
        **invoice.model_dump(),
        "profile": ZUGFeRDProfile.XRECHNUNG,
        "syntax": XRechnungSyntax.UBL,
        "buyer_reference": invoice.buyer_reference or invoice.invoice_number,
    })
    xml_bytes = XRechnungUBLSerializer().serialize(xrechnung, pretty_print=False)

    transmitter = PeppolTransmitter(credentials=credentials, environment=env)

    try:
        receipt = await transmitter.transmit(
            invoice_xml=xml_bytes,
            recipient_id=recipient,
            sender_id=params.sender_id,
        )
    except (PlatformError, EInvoicingError) as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    output = PeppolSendOutput(
        message_id=receipt.ref_to_message_id,
        receipt_message_id=receipt.message_id,
        recipient_id=str(recipient),
    )
    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
