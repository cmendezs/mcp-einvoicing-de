"""MCP tool: peppol_check — verify German Peppol participant registration.

Performs a DNS-based SMP (Service Metadata Publisher) lookup to verify
whether a company is registered on the Peppol network and accepts
BIS Billing 3.0 documents (DE PINT profile).

Peppol SMP lookup flow:
  1. Hash participant ID using SHA-256 (Peppol SML DNS scheme)
  2. Query DNS: B-<sha256hash>.iso6523-actorid-upis.<sml-domain>
  3. Fetch SMP record to get capabilities
  4. Check for DocumentTypeIdentifier matching BIS Billing 3.0

German Peppol Authority: [NEED: confirm German Peppol Authority — likely OpenPeppol DE]
SML domain for production: [NEED: confirm — edelivery.eu? or sml.peppolcentral.org?]
SML domain for test: [NEED: confirm test SML domain]

Peppol participant ID formats for Germany:
  - GLN: 0088:<gln>
  - Leitweg-ID: 0204:<leitweg-id>
  - VAT DE: 9930:DE<vat_number>
  - [NEED: confirm all EAS codes accepted for German e-invoicing]

[NEED: verify if mcp-einvoicing-core provides a PeppolClient base class]
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
import mcp.types as types
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_PEPPOL_SMP_URL = os.environ.get("EINVOICING_DE_PEPPOL_SMP_URL", "")
# [NEED: confirm production and test SML base URLs]
_SML_DOMAIN_PRODUCTION = "edelivery.eu"  # [NEED: verify]
_SML_DOMAIN_TEST = "acc.edelivery.eu"  # [NEED: verify]


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
        "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1",
        description=(
            "Peppol document type identifier to check capability for. "
            "Defaults to BIS Billing 3.0. "
            "[NEED: confirm DE PINT document type identifier]"
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
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    # TODO: implement Peppol SMP lookup
    # Steps:
    #   1. URL-encode participant_id as ISO 6523 actor ID
    #   2. SHA-256 hash the participant ID (Peppol DNS scheme)
    #   3. Construct DNS name: B-<hash>.<scheme>.<sml_domain>
    #   4. DNS SRV/A lookup to find the SMP host
    #   5. HTTP GET to SMP: https://<smp_host>/<participant_id>/services/<doc_type>
    #   6. Parse XML response to extract AS4 endpoint URL
    # [NEED: implement DNS lookup — use dnspython or httpx to query public DNS-over-HTTPS]
    # [NEED: verify exact DNS name construction for Peppol SML]
    # [NEED: verify SMP API path format]
    # [NEED: verify if mcp-einvoicing-core provides PeppolSMPClient]

    output = PeppolCheckOutput(
        is_registered=False,
        participant_id=params.participant_id,
        error="Peppol SMP lookup not yet implemented. [NEED: implement DNS + SMP lookup]",
    )

    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
