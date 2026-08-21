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

import logging
import os
import warnings
from typing import Any

from mcp_einvoicing_core.exceptions import EInvoicingError
from mcp_einvoicing_core.xml_utils import format_error, resolve_xml_input
from pydantic import BaseModel, Field, field_validator, model_validator

from mcp_einvoicing_de.utils.xml_utils import detect_invoice_syntax, detect_zugferd_profile
from mcp_einvoicing_de.validators.kosit import KoSITValidator
from mcp_einvoicing_de.validators.schematron import (
    SchematronValidator,
    ValidationMessage,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# DE-LC-1: cloud validation is opt-in. EINVOICING_DE_KOSIT_ENABLE=1 turns it on
# globally; the legacy EINVOICING_DE_KOSIT_DISABLE kill-switch is honoured for
# one release as a hard override (logged as deprecated) since "disable" no
# longer has a meaningful default state to disable.
_KOSIT_ENABLE_ENV = os.environ.get("EINVOICING_DE_KOSIT_ENABLE", "").strip() == "1"
_KOSIT_DISABLE_ENV_LEGACY = os.environ.get("EINVOICING_DE_KOSIT_DISABLE", "").strip() == "1"
if _KOSIT_DISABLE_ENV_LEGACY:
    logger.warning(
        "EINVOICING_DE_KOSIT_DISABLE is deprecated: cloud validation now "
        "defaults to off, so this variable has no effect except as a hard "
        "override that blocks cloud_validate=True. Use "
        "EINVOICING_DE_KOSIT_ENABLE=1 to opt in to cloud validation instead."
    )


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
    cloud_validate: bool = Field(
        False,
        description=(
            "By default this validator runs entirely locally (Schematron only). "
            "Set cloud_validate=True (or EINVOICING_DE_KOSIT_ENABLE=1) to opt in "
            "to sending the invoice XML to a remote KoSIT endpoint. Doing so "
            "egresses the full invoice payload."
        ),
    )
    use_local_only: bool | None = Field(
        None,
        description=(
            "[Deprecated] Use cloud_validate instead. use_local_only=True is "
            "equivalent to cloud_validate=False, which is now the default; "
            "this alias is retained for one release and will be removed."
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

    @model_validator(mode="after")
    def _apply_deprecated_use_local_only_alias(self) -> InvoiceValidateInput:
        if self.use_local_only is not None:
            warnings.warn(
                "use_local_only is deprecated; use cloud_validate instead "
                "(use_local_only=True is equivalent to cloud_validate=False, "
                "which is now the default).",
                DeprecationWarning,
                stacklevel=2,
            )
            object.__setattr__(self, "cloud_validate", not self.use_local_only)
        return self

    def get_xml_bytes(self) -> bytes:
        """Resolve xml_content / xml_base64 to raw bytes."""
        return resolve_xml_input(self.xml_content, self.xml_base64)


class ValidationFinding(BaseModel):
    """Single validation finding."""

    severity: str
    rule_id: str
    location: str
    text: str
    source: str = Field(
        "",
        description=(
            "Stylesheet key that produced this finding (e.g. 'en16931_cii', "
            "'xrechnung_cii'). Empty when the finding did not come from a "
            "chained local Schematron run (e.g. KoSIT cloud results)."
        ),
    )


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

# ── Implementation ────────────────────────────────────────────────────────────

_PROFILE_TO_STYLESHEET: dict[str, dict[str, list[str]]] = {
    # Maps (profile_enum_name, syntax) → ordered list of stylesheet keys (see
    # validators/schematron.py). Each profile uses its own FeRD compiled
    # Schematron so that rules permitting optional fields in lower profiles
    # (MINIMUM, BASIC-WL) are not incorrectly applied as errors by the
    # stricter EN 16931 ruleset.
    #
    # XRECHNUNG chains the CEN EN 16931 base ruleset ahead of the KoSIT
    # XRechnung CIUS ruleset: the bundled XRechnung-*-validation.xsl files
    # only encode the BR-DE-* / CIUS-specific rules, not the underlying
    # EN 16931 base rules (DE-SC-2) — running the CIUS stylesheet alone
    # silently skips base-rule violations.
    "MINIMUM":   {"CII": ["zugferd_minimum_cii"]},
    "BASIC_WL":  {"CII": ["zugferd_basicwl_cii"]},
    "BASIC":     {"CII": ["zugferd_basic_cii"]},
    "EN_16931":  {"CII": ["en16931_cii"], "UBL": ["en16931_ubl"]},
    "EXTENDED":  {"CII": ["zugferd_extended_cii"]},
    "XRECHNUNG": {
        "CII": ["en16931_cii", "xrechnung_cii"],
        "UBL": ["en16931_ubl", "xrechnung_ubl"],
    },
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
    """Run local Schematron validation.

    For profiles that map to more than one stylesheet key (XRECHNUNG chains
    the EN 16931 base ruleset ahead of the KoSIT CIUS ruleset — DE-SC-2),
    every stylesheet in the list is run and findings are merged: errors and
    warnings are concatenated, and ``is_valid`` is the boolean AND across all
    runs. Each merged ``ValidationMessage`` carries a dynamic ``source``
    attribute (the stylesheet key that produced it) so callers can tell which
    ruleset fired; this is DE-local and does not require a core schema change.
    """
    stylesheet_map = _PROFILE_TO_STYLESHEET.get(profile_name, {})
    stylesheet_keys = stylesheet_map.get(syntax)

    if not stylesheet_keys:
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

    merged = ValidationResult(is_valid=True, profile=profile_name, syntax=syntax)
    for stylesheet_key in stylesheet_keys:
        result = _run_one_stylesheet(xml_bytes, stylesheet_key, profile_name, syntax)
        for msg in result.errors + result.warnings:
            msg.source = stylesheet_key  # type: ignore[attr-defined]
        merged.errors.extend(result.errors)
        merged.warnings.extend(result.warnings)
        merged.is_valid = merged.is_valid and result.is_valid

    return merged


def _run_one_stylesheet(
    xml_bytes: bytes, stylesheet_key: str, profile_name: str, syntax: str
) -> ValidationResult:
    """Run a single bundled Schematron stylesheet and return its result."""
    from mcp_einvoicing_de.validators.schematron import ValidationMessage

    try:
        validator = SchematronValidator(stylesheet_key)
    except FileNotFoundError as exc:
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
    except (ImportError, ValueError) as exc:
        # The DE factory in validators/schematron.py delegates to core's
        # load_schematron_validator(), which dispatches to the XSLT 2.0 Saxon
        # backend for FeRD Factur-X stylesheets. When the optional ``saxonche``
        # extra is not installed, core raises ImportError with an install hint;
        # a ValueError here means Saxon could not compile the stylesheet.
        # Return a structured error so callers can present it either way.
        logger.warning("Schematron backend unavailable for key=%s: %s", stylesheet_key, exc)
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


async def invoice_validate(
    xml_content: str | None = None,
    xml_base64: str | None = None,
    profile: str | None = None,
    syntax: str | None = None,
    cloud_validate: bool = False,
    use_local_only: bool | None = None,
    kosit_strict: bool = False,
    strict: bool = True,
) -> dict[str, Any]:
    """Validate a ZUGFeRD 2.x or XRechnung 3.x invoice XML.

    Checks against EN 16931 rules and German KoSIT Schematron rules
    (BR-DE-* business rules). Returns a structured validation report with
    errors and warnings. Supports all ZUGFeRD profiles (MINIMUM through
    EXTENDED) and XRechnung (CII and UBL syntax). Profile and syntax are
    auto-detected if not specified. By default this validator runs
    entirely locally (Schematron only). Set cloud_validate=True (or
    EINVOICING_DE_KOSIT_ENABLE=1) to opt in to sending the invoice XML to
    a remote KoSIT endpoint. Doing so egresses the full invoice payload.

    Args:
        xml_content: Raw XML string of the invoice to validate. Provide
            either xml_content or xml_base64, not both.
        xml_base64: Base64-encoded XML bytes of the invoice.
        profile: Override profile detection. One of: MINIMUM, BASIC_WL,
            BASIC, EN_16931, EXTENDED, XRECHNUNG. If omitted, auto-detected
            from the XML GuidelineID.
        syntax: Override syntax detection. One of: CII, UBL. If omitted,
            auto-detected from the XML root element namespace.
        cloud_validate: Opt in to sending the invoice XML to a remote
            KoSIT endpoint (egresses the full invoice payload). Local
            Schematron only by default.
        use_local_only: [Deprecated] Use cloud_validate instead.
            use_local_only=True is equivalent to cloud_validate=False,
            which is now the default; this alias is retained for one
            release and will be removed.
        kosit_strict: If True, fail hard when the KoSIT cloud validator is
            unreachable instead of falling back to local Schematron.
        strict: If True, warnings are also reported. If False, only
            errors are returned.
    """
    params = InvoiceValidateInput(
        xml_content=xml_content,
        xml_base64=xml_base64,
        profile=profile,
        syntax=syntax,
        cloud_validate=cloud_validate,
        use_local_only=use_local_only,
        kosit_strict=kosit_strict,
        strict=strict,
    )

    try:
        xml_bytes = params.get_xml_bytes()
    except (ValueError, EInvoicingError) as exc:
        return format_error(str(exc))

    profile_name = _resolve_profile(params.profile, xml_bytes)
    syntax = _resolve_syntax(params.syntax, xml_bytes)

    use_cloud = (params.cloud_validate or _KOSIT_ENABLE_ENV) and not _KOSIT_DISABLE_ENV_LEGACY

    validator_used: str
    if not use_cloud:
        result = await _validate_local(xml_bytes, profile_name, syntax)
        validator_used = "local_schematron"
    else:
        # DE-LC-2: no implicit default URL — the caller opting into cloud
        # validation gets the explicitly-named [Unverified] sentinel unless
        # a real endpoint is configured via EINVOICING_DE_KOSIT_VALIDATOR_URL.
        kosit = KoSITValidator(KoSITValidator._UNVERIFIED_DEFAULT_KOSIT_URL)
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
            severity=e.severity,
            rule_id=e.rule_id,
            location=e.location,
            text=e.text,
            source=getattr(e, "source", ""),
        )
        for e in result.errors
    ]
    findings_warnings = [
        ValidationFinding(
            severity=w.severity,
            rule_id=w.rule_id,
            location=w.location,
            text=w.text,
            source=getattr(w, "source", ""),
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

    return output.model_dump()
