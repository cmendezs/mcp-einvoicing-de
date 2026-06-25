"""MCP tool: invoice_validate — validate ZUGFeRD / XRechnung invoices.

Applies a two-stage validation pipeline:
1. XML well-formedness check (lxml parse)
2. Profile/syntax auto-detection
3. EN 16931 Schematron rules (local XSLT)
4. KoSIT XRechnung BR-DE-* rules (local XSLT or remote KoSIT validator)

Official rule sources:
- EN 16931: [NEED: CEN GitLab URL]
- XRechnung: https://github.com/itplr-kosit/xrechnung-schematron
- KoSIT Validierungstool: https://github.com/itplr-kosit/validationtool
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import mcp.types as types
from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.xml_utils import format_error, resolve_xml_input
from pydantic import BaseModel, Field, field_validator

from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile
from mcp_einvoicing_de.validators.kosit import KoSITValidator
from mcp_einvoicing_de.validators.schematron import (
    SchematronValidator,
    ValidationMessage,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_KOSIT_DISABLED = os.environ.get("EINVOICING_DE_KOSIT_DISABLE", "").strip() == "1"


# ── Input / Output schemas ────────────────────────────────────────────────────


class InvoiceValidateInput(BaseModel):
    """Input schema for the invoice_validate tool."""

    xml_content: str | None = Field(
        None,
        description=(
            "Raw XML string of the invoice to validate. "
            "Provide either xml_content or xml_base64, not both."
        ),
    )
    xml_base64: str | None = Field(
        None,
        description=(
            "Base64-encoded XML bytes of the invoice. "
            "Useful when the XML contains characters that are problematic in JSON strings."
        ),
    )
    profile: str | None = Field(
        None,
        description=(
            "Override profile detection. One of: MINIMUM, BASIC_WL, BASIC, EN_16931, "
            "EXTENDED, XRECHNUNG. If omitted, auto-detected from the XML GuidelineID."
        ),
    )
    syntax: str | None = Field(
        None,
        description=(
            "Override syntax detection. One of: CII, UBL. "
            "If omitted, auto-detected from the XML root element namespace."
        ),
    )
    use_local_only: bool = Field(
        False,
        description=(
            "If True, skip the KoSIT cloud validator and use only local Schematron. "
            "By default KoSIT cloud validation is attempted first with Schematron fallback."
        ),
    )
    kosit_strict: bool = Field(
        False,
        description=(
            "If True, fail hard when the KoSIT cloud validator is unreachable instead "
            "of falling back to local Schematron."
        ),
    )
    strict: bool = Field(
        True,
        description="If True, warnings are also reported. If False, only errors are returned.",
    )

    @field_validator("xml_content", "xml_base64", mode="before")
    @classmethod
    def at_least_one_source(cls, v: Any, info: Any) -> Any:
        # Cross-field validation happens in model_validator; this is a pass-through
        return v

    def get_xml_bytes(self) -> bytes:
        """Resolve xml_content / xml_base64 to raw bytes."""
        return resolve_xml_input(self.xml_content, self.xml_base64)


class ValidationFinding(BaseModel):
    """Single validation finding."""

    severity: str
    rule_id: str
    location: str
    text: str


class InvoiceValidateOutput(BaseModel):
    """Output schema for the invoice_validate tool."""

    is_valid: bool = Field(..., description="True if no errors were found")
    profile: str = Field(..., description="Detected or overridden ZUGFeRD profile")
    syntax: str = Field(..., description="Detected or overridden XML syntax (CII or UBL)")
    error_count: int
    warning_count: int
    errors: list[ValidationFinding]
    warnings: list[ValidationFinding]
    validator_used: str = Field(
        ..., description="'local_schematron' or 'kosit_remote'"
    )


# ── MCP Tool definition ───────────────────────────────────────────────────────

TOOL_INVOICE_VALIDATE = types.Tool(
    name="invoice_validate",
    description=(
        "Validate a ZUGFeRD 2.x or XRechnung 3.x invoice XML against EN 16931 rules "
        "and German KoSIT Schematron rules (BR-DE-* business rules). "
        "Returns a structured validation report with errors and warnings. "
        "Supports all ZUGFeRD profiles (MINIMUM through EXTENDED) and XRechnung "
        "(CII and UBL syntax). Profile and syntax are auto-detected if not specified."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "xml_content": {
                "type": "string",
                "description": "Raw XML string of the invoice to validate.",
            },
            "xml_base64": {
                "type": "string",
                "description": "Base64-encoded XML bytes of the invoice.",
            },
            "profile": {
                "type": "string",
                "enum": ["MINIMUM", "BASIC_WL", "BASIC", "EN_16931", "EXTENDED", "XRECHNUNG"],
                "description": "Override profile detection.",
            },
            "syntax": {
                "type": "string",
                "enum": ["CII", "UBL"],
                "description": "Override syntax detection.",
            },
            "use_local_only": {
                "type": "boolean",
                "default": False,
                "description": "Skip KoSIT cloud; use only local Schematron.",
            },
            "kosit_strict": {
                "type": "boolean",
                "default": False,
                "description": "Fail hard when KoSIT is unreachable (no fallback).",
            },
            "strict": {
                "type": "boolean",
                "default": True,
                "description": "Include warnings in output.",
            },
        },
        "anyOf": [
            {"required": ["xml_content"]},
            {"required": ["xml_base64"]},
        ],
    },
)


# ── Implementation ────────────────────────────────────────────────────────────

_PROFILE_TO_STYLESHEET: dict[str, dict[str, str]] = {
    # Maps (profile_enum_name, syntax) → stylesheet key (see validators/schematron.py).
    # Each profile uses its own FeRD compiled Schematron so that rules permitting
    # optional fields in lower profiles (MINIMUM, BASIC-WL) are not incorrectly
    # applied as errors by the stricter EN 16931 ruleset.
    "MINIMUM":   {"CII": "zugferd_minimum_cii"},
    "BASIC_WL":  {"CII": "zugferd_basicwl_cii"},
    "BASIC":     {"CII": "zugferd_basic_cii"},
    "EN_16931":  {"CII": "en16931_cii", "UBL": "en16931_ubl"},
    "EXTENDED":  {"CII": "zugferd_extended_cii"},
    "XRECHNUNG": {"CII": "xrechnung_cii", "UBL": "xrechnung_ubl"},
}


def _resolve_profile(profile_str: str | None, xml_bytes: bytes) -> str:
    """Return the normalised profile name (enum key, e.g. 'EN_16931')."""
    if profile_str:
        return profile_str.upper().replace(" ", "_")
    detected = detect_zugferd_profile(xml_bytes)
    if detected is None:
        logger.warning("Could not auto-detect ZUGFeRD profile; defaulting to EN_16931")
        return "EN_16931"
    # Convert ZUGFeRDProfile enum value to its name
    return detected.name


def _resolve_syntax(syntax_str: str | None, xml_bytes: bytes) -> str:
    """Return 'CII' or 'UBL'."""
    if syntax_str:
        return syntax_str.upper()
    try:
        return detect_invoice_syntax(xml_bytes).value
    except ValueError:
        logger.warning("Could not auto-detect invoice syntax; defaulting to CII")
        return "CII"


async def _validate_local(
    xml_bytes: bytes, profile_name: str, syntax: str
) -> ValidationResult:
    """Run local Schematron validation."""
    stylesheet_map = _PROFILE_TO_STYLESHEET.get(profile_name, {})
    stylesheet_key = stylesheet_map.get(syntax)

    if stylesheet_key is None:
        logger.warning(
            "No Schematron stylesheet for profile=%s syntax=%s; skipping Schematron",
            profile_name,
            syntax,
        )
        from mcp_einvoicing_de.validators.schematron import ValidationMessage

        return ValidationResult(
            is_valid=True,
            warnings=[
                ValidationMessage(
                    severity="warning",
                    rule_id="NO-STYLESHEET",
                    location="/",
                    text=(
                        f"No Schematron stylesheet available for "
                        f"profile={profile_name} syntax={syntax}. "
                        "Only XML well-formedness was checked. "
                        "[NEED: add stylesheet for this combination]"
                    ),
                )
            ],
            profile=profile_name,
            syntax=syntax,
        )

    try:
        validator = SchematronValidator(stylesheet_key)
    except FileNotFoundError as exc:
        from mcp_einvoicing_de.validators.schematron import ValidationMessage

        return ValidationResult(
            is_valid=False,
            errors=[
                ValidationMessage(
                    severity="error",
                    rule_id="STYLESHEET-MISSING",
                    location="/",
                    text=str(exc),
                )
            ],
            profile=profile_name,
            syntax=syntax,
        )
    except ValueError as exc:
        # The DE factory in validators/schematron.py dispatches to the
        # XSLT 2.0 Saxon backend for FeRD Factur-X stylesheets. When the optional
        # ``saxonche`` extra is not installed, the factory raises ValueError with
        # an install hint. Return a structured error so callers can present it.
        logger.warning("Schematron backend unavailable for key=%s: %s", stylesheet_key, exc)
        from mcp_einvoicing_de.validators.schematron import ValidationMessage

        return ValidationResult(
            is_valid=False,
            errors=[
                ValidationMessage(
                    severity="error",
                    rule_id="STYLESHEET-XSLT2-BACKEND-MISSING",
                    location="/",
                    text=(
                        f"Schematron stylesheet {stylesheet_key!r} requires an "
                        "XSLT 2.0 backend. Install the optional extra with "
                        "`pip install mcp-einvoicing-de[xslt2]`, or set "
                        "use_remote_kosit=True to use the KoSIT cloud validator. "
                        f"Detail: {exc}"
                    ),
                )
            ],
            profile=profile_name,
            syntax=syntax,
        )

    return validator.validate(xml_bytes, profile=profile_name, syntax=syntax)


async def handle_invoice_validate(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for invoice_validate."""
    try:
        params = InvoiceValidateInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        xml_bytes = params.get_xml_bytes()
    except (ValueError, EInvoicingError) as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    profile_name = _resolve_profile(params.profile, xml_bytes)
    syntax = _resolve_syntax(params.syntax, xml_bytes)

    validator_used: str
    if params.use_local_only or _KOSIT_DISABLED:
        result = await _validate_local(xml_bytes, profile_name, syntax)
        validator_used = "local_schematron"
    else:
        kosit = KoSITValidator()
        kosit_result = await kosit.validate(xml_bytes)
        kosit_failed = any(
            e.rule_id == "KOSIT-HTTP" for e in kosit_result.errors
        )
        if kosit_failed and not params.kosit_strict:
            logger.warning("KoSIT cloud unreachable, falling back to local Schematron")
            result = await _validate_local(xml_bytes, profile_name, syntax)
            result.warnings.append(
                ValidationMessage(
                    severity="warning",
                    rule_id="KOSIT-FALLBACK",
                    location="/",
                    text="KoSIT cloud validator was unreachable; results are from local Schematron.",
                )
            )
            validator_used = "schematron_fallback"
        else:
            result = kosit_result
            result.profile = profile_name
            result.syntax = syntax
            validator_used = "kosit_cloud"

    findings_errors = [
        ValidationFinding(
            severity=e.severity, rule_id=e.rule_id, location=e.location, text=e.text
        )
        for e in result.errors
    ]
    findings_warnings = [
        ValidationFinding(
            severity=w.severity, rule_id=w.rule_id, location=w.location, text=w.text
        )
        for w in result.warnings
    ] if params.strict else []

    output = InvoiceValidateOutput(
        is_valid=result.is_valid,
        profile=profile_name,
        syntax=syntax,
        error_count=len(result.errors),
        warning_count=len(result.warnings),
        errors=findings_errors,
        warnings=findings_warnings,
        validator_used=validator_used,
    )

    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
