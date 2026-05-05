"""MCP tool: peppol_check — verify German Peppol participant registration.

Performs a DNS-based SMP (Service Metadata Publisher) lookup to verify
whether a company is registered on the Peppol network and accepts
BIS Billing 3.0 documents (DE PINT profile).

Peppol SMP lookup flow:
  1. Hash participant ID using SHA-256 (Peppol SML DNS scheme)
     [Unverified: confirm hash algorithm against current OpenPeppol BDMSL spec]
  2. Query DNS (via DNS-over-HTTPS): B-<sha256>.<scheme>.iso6523-actorid-upis.<sml>
  3. Fetch SMP service group to enumerate supported document types
  4. Fetch SMP service metadata to get the AS4 endpoint URL

German Peppol Authority: [NEED: confirm German Peppol Authority name]
SML domain (production): edelivery.tech.ec.europa.eu  [Unverified]
SML domain (test):       acc.edelivery.tech.ec.europa.eu  [Unverified]

Peppol participant ID formats for Germany:
  - GLN: 0088:<gln>
  - Leitweg-ID: 0204:<leitweg-id>
  - VAT DE: 9930:DE<vat_number>
  [NEED: confirm all EAS codes accepted for German e-invoicing B2B mandate]
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types
from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.peppol import (
    PEPPOL_BIS_BILLING_30,
    PeppolEnvironment,
    PeppolParticipantId,
    PeppolSMPClient,
)
from mcp_einvoicing_core.xml_utils import format_error
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PeppolCheckInput(BaseModel):
    """Input schema for peppol_check."""

    participant_id: str = Field(
        ...,
        description=(
            "Peppol participant identifier in the format <scheme>:<value>. "
            "Examples: '0204:991-1234512345-06' (Leitweg-ID), "
            "'0088:4012345678901' (GLN), '9930:DE123456789' (VAT)."
        ),
    )
    document_type: str = Field(
        PEPPOL_BIS_BILLING_30,
        description=(
            "Peppol document type identifier to check capability for. "
            "Defaults to BIS Billing 3.0. "
            "[NEED: confirm DE PINT document type identifier once standardised]"
        ),
    )
    environment: str = Field(
        "production",
        description="Peppol environment: 'production' or 'test'.",
    )


class PeppolCheckOutput(BaseModel):
    """Output schema for peppol_check."""

    is_registered: bool
    participant_id: str
    document_type_supported: bool | None = Field(
        None, description="True if the participant supports the requested document type."
    )
    access_point_url: str | None = Field(
        None, description="AS4 endpoint URL of the participant's access point."
    )
    transport_profile: str | None = None
    lookup_details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


TOOL_PEPPOL_CHECK = types.Tool(
    name="peppol_check",
    description=(
        "Verify whether a German company is registered on the Peppol network "
        "and can receive electronic invoices via AS4. "
        "Performs a live DNS + SMP lookup using the participant's Peppol ID "
        "(Leitweg-ID, GLN, or VAT number). "
        "Returns registration status, supported document types, and AS4 endpoint URL."
    ),
    inputSchema={
        "type": "object",
        "required": ["participant_id"],
        "properties": {
            "participant_id": {
                "type": "string",
                "description": "Peppol participant ID, e.g. '0204:991-1234512345-06'.",
            },
            "document_type": {
                "type": "string",
                "description": "Peppol document type identifier (default: BIS Billing 3.0).",
            },
            "environment": {
                "type": "string",
                "enum": ["production", "test"],
                "default": "production",
            },
        },
    },
)


async def handle_peppol_check(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for peppol_check."""
    try:
        params = PeppolCheckInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        pid = PeppolParticipantId.parse(params.participant_id)
    except ValueError as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    environment = (
        PeppolEnvironment.TEST
        if params.environment == "test"
        else PeppolEnvironment.PRODUCTION
    )
    client = PeppolSMPClient(environment=environment)

    try:
        lookup = await client.lookup_participant(pid)
    except EInvoicingError as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    document_type_supported: bool | None = None
    access_point_url: str | None = None
    transport_profile: str | None = None

    if lookup.is_registered and params.document_type:
        document_type_supported = params.document_type in lookup.supported_document_types
        if document_type_supported:
            try:
                service = await client.get_service_endpoint(
                    pid, params.document_type, smp_hostname=lookup.smp_hostname
                )
                access_point_url = service.endpoint_url
                transport_profile = service.transport_profile
            except EInvoicingError as exc:
                logger.warning("Service endpoint fetch failed: %s", exc)

    output = PeppolCheckOutput(
        is_registered=lookup.is_registered,
        participant_id=str(pid),
        document_type_supported=document_type_supported,
        access_point_url=access_point_url,
        transport_profile=transport_profile,
        lookup_details=lookup.to_dict(),
        error=lookup.error,
    )
    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
