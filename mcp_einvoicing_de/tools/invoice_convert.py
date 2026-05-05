"""MCP tool: invoice_convert — convert between ZUGFeRD profiles or ZUGFeRD ↔ XRechnung.

Supported conversions:
- ZUGFeRD profile upgrade: MINIMUM → BASIC_WL → BASIC → EN_16931 → EXTENDED
- ZUGFeRD profile downgrade (data loss risk — flagged in output)
- ZUGFeRD EN_16931 ↔ XRechnung CII (same CII syntax, different profile URN + BR-DE rules)
- ZUGFeRD EN_16931 → XRechnung UBL (syntax transformation)
- XRechnung UBL → XRechnung CII (syntax transformation)

Conversions from EXTENDED to any other profile will result in data loss for
EXTENDED-only elements. These are flagged as warnings in the output.

[NEED: verify if mcp-einvoicing-core provides a ConversionEngine base class]
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types
from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.xml_utils import format_error, resolve_xml_input
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InvoiceConvertInput(BaseModel):
    """Input schema for invoice_convert."""

    xml_content: str | None = Field(None, description="Raw XML string of the source invoice.")
    xml_base64: str | None = Field(None, description="Base64-encoded XML bytes.")
    target_profile: str = Field(
        ...,
        description=(
            "Target profile. One of: MINIMUM, BASIC_WL, BASIC, EN_16931, EXTENDED, XRECHNUNG."
        ),
    )
    target_syntax: str = Field(
        "CII",
        description="Target syntax: 'CII' or 'UBL'. UBL is only valid for XRECHNUNG.",
    )
    allow_data_loss: bool = Field(
        False,
        description=(
            "If True, allow profile downgrades that discard data. "
            "Discarded fields are listed in the output. "
            "If False and data loss would occur, the conversion is rejected."
        ),
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


TOOL_INVOICE_CONVERT = types.Tool(
    name="invoice_convert",
    description=(
        "Convert a ZUGFeRD or XRechnung invoice to a different profile or syntax. "
        "Supports ZUGFeRD profile upgrades and downgrades, ZUGFeRD ↔ XRechnung conversion, "
        "and CII ↔ UBL syntax transformation (XRechnung only). "
        "Profile downgrades may result in data loss; set allow_data_loss=True to permit this."
    ),
    inputSchema={
        "type": "object",
        "required": ["target_profile"],
        "properties": {
            "xml_content": {"type": "string"},
            "xml_base64": {"type": "string"},
            "target_profile": {
                "type": "string",
                "enum": ["MINIMUM", "BASIC_WL", "BASIC", "EN_16931", "EXTENDED", "XRECHNUNG"],
            },
            "target_syntax": {"type": "string", "enum": ["CII", "UBL"], "default": "CII"},
            "allow_data_loss": {"type": "boolean", "default": False},
        },
        "anyOf": [{"required": ["xml_content"]}, {"required": ["xml_base64"]}],
    },
)


async def handle_invoice_convert(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for invoice_convert."""
    try:
        params = InvoiceConvertInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        resolve_xml_input(params.xml_content, params.xml_base64)
    except (ValueError, EInvoicingError) as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    # TODO: implement conversion pipeline
    # Steps:
    #   1. Parse source XML → ZUGFeRDInvoice model (via invoice_parse logic)
    #   2. Detect source profile and syntax
    #   3. Validate conversion path (upgrade vs. downgrade, data loss check)
    #   4. Apply profile-specific field pruning for downgrades
    #   5. Update GuidelineID URN to target profile
    #   6. Re-serialise to CII or UBL XML
    #   7. Collect data_loss_warnings and conversion_notes
    # [NEED: define conversion matrix (which fields are mandatory per profile)]
    # [NEED: verify if mcp-einvoicing-core provides a profile compatibility matrix]

    return [
        types.TextContent(
            type="text",
            text=json.dumps(
                {
                    "error": "Conversion not yet implemented.",
                    "target_profile": params.target_profile,
                    "target_syntax": params.target_syntax,
                    "hint": "TODO: implement conversion pipeline",
                }
            ),
        )
    ]
