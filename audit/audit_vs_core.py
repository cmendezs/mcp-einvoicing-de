"""Pre-publish audit: verify mcp-einvoicing-de coherence against mcp-einvoicing-core.

Run standalone:
    python audit/audit_vs_core.py
    python audit/audit_vs_core.py --output audit/report.json
    python audit/audit_vs_core.py --fail-on blocking   # exits 2 on blocking failures
    python audit/audit_vs_core.py --fail-on warnings   # exits 1 on warnings, 2 on blocking

Exit codes:
    0  All checks passed
    1  Warnings only (non-blocking)
    2  Blocking failures found

This script is designed to be importable with no side effects; all execution
is guarded by `if __name__ == "__main__"`.

CHECK 1 and CHECK 4 are delegated to mcp_einvoicing_core.audit.
CHECK 2 (tool registry), CHECK 3 (model field alignment), and CHECK 5
(DE-specific structural) are implemented here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp_einvoicing_core.audit import (
    SEVERITY_BLOCKING,
    SEVERITY_OK,
    SEVERITY_WARNING,
    AuditReport,
    CheckFinding,
    CheckResult,
    _try_import,
    make_report,
    parse_audit_args,
    render_summary_table,
    run_check_core_coverage,
    run_check_version_compatibility,
)

# ---------------------------------------------------------------------------
# CHECK 1 configuration — country-specific constants
# ---------------------------------------------------------------------------

# ZUGFeRDInvoice now extends EN16931Invoice (and component classes extend their EN16931
# counterparts). The WRONG_BASE_CLASS BLOCKING is resolved. The overrides below cover
# symbols that are internal to each core module (stdlib/Pydantic imports used within
# core itself) or belong to subsystems DE deliberately does not use.
_INTENTIONAL_OVERRIDES: dict[str, set[str]] = {
    # DE implements tool functions directly rather than subclassing the ABC base classes.
    # EInvoicingMCPServer is unused because DE uses a standalone FastMCP server.
    # Remaining symbols are internal imports of base_server.py not used by DE.
    "mcp_einvoicing_core.base_server": {
        "ABC",
        "Any",
        "BaseDocumentGenerator",
        "BaseDocumentParser",
        "BaseDocumentValidator",
        "BaseLifecycleManager",
        "BaseModel",
        "BasePartyValidator",
        "DocumentValidationResult",
        "EInvoicingMCPServer",
        "FastMCP",
        "Field",
        "InvoiceDocument",
        "InvoiceParty",
        "SubmitResult",
        "TaxIdValidationResult",
        "abstractmethod",
        "assert_not_read_only",
        "scrub",
    },
    # XAdES signing is ES-specific (Facturae / TicketBAI). DE applies no
    # document-level signing for ZUGFeRD or XRechnung.
    # Remaining symbols are internal imports of digital_signature.py.
    "mcp_einvoicing_core.digital_signature": {
        "ABC",
        "BaseDocumentSigner",
        "XAdESEPESSigner",
        "XAdESSignerConfig",
        "abstractmethod",
        "dataclass",
        "datetime",
        "field",
        "timezone",
    },
    # download_rules is not used by DE — ZUGFeRD/XRechnung validators are bundled
    # or downloaded via a package-specific mechanism.
    "mcp_einvoicing_core.download_rules": {
        "DownloadSpec",
        "Path",
        "dataclass",
        "download_artefacts",
        "entry_points",
        "field",
        "main",
    },
    # EN16931 component and invoice classes are now used as base classes (e.g.
    # ZUGFeRDAddress extends EN16931Address). The symbols below are internal
    # stdlib/Pydantic imports used within en16931.py itself; DE does not import
    # them from core.
    "mcp_einvoicing_core.en16931": {
        "BaseModel",
        "Decimal",
        "Field",
        "date",
        "field_validator",
        "model_validator",
    },
    # Exception hierarchy: DE imports EInvoicingError and PlatformError from core.
    # The remaining exception subclasses are not used by DE.
    "mcp_einvoicing_core.exceptions": {
        "AuthenticationError",
        "DocumentGenerationError",
        "PartyValidationError",
        "SchematronValidationError",
        "ValidationError",
        "XSDValidationError",
    },
    # OAuth2 client and types: DE has no live clearance API. ZUGFeRD and XRechnung
    # are post-audit formats; no government endpoint interaction is required.
    # Remaining symbols are internal imports of http_client.py.
    "mcp_einvoicing_core.http_client": {
        "Any",
        "AuthMode",
        "AuthenticationError",
        "BaseEInvoicingClient",
        "BaseEInvoicingConfig",
        "BaseModel",
        "BaseSettings",
        "Enum",
        "Field",
        "OAuthConfig",
        "OAuthValues",
        "Path",
        "TokenCache",
        "field_validator",
        "parsedate_to_datetime",
        "urlparse",
    },
    # The country-agnostic InvoiceDocument tree is not used for ZUGFeRD/XRechnung
    # generation. DE uses the EN16931Invoice-derived hierarchy instead.
    # Remaining symbols are internal imports of models.py.
    "mcp_einvoicing_core.models": {
        "BaseModel",
        "Decimal",
        "DocumentValidationResult",
        "Field",
        "InvoiceDocument",
        "InvoiceLineItem",
        "InvoiceParty",
        "PartyAddress",
        "PaymentTerms",
        "TaxIdValidationResult",
        "TaxIdentifier",
        "VATSummary",
        "field_validator",
        "model_validator",
    },
    # PDF embedding: ZUGFeRD uses PDF/A-3 with embedded CII XML, but DE implements
    # this via its own pdf utility; the core PDFEmbedder is unused.
    "mcp_einvoicing_core.pdf": {
        "PDFEmbedder",
    },
    # Peppol: DE imports PeppolEnvironment, PeppolParticipantId, and PeppolSMPClient
    # for peppol_check. The remaining types and module-internal symbols are not used.
    "mcp_einvoicing_core.peppol": {
        "Enum",
        "PeppolLookupResult",
        "PeppolServiceInfo",
        "dataclass",
        "field",
    },
    # profile_registry: DE registers profiles via the module-level singleton.
    # The class, factory, and internal imports are not used directly.
    "mcp_einvoicing_core.profile_registry": {
        "ProfileEntry",
        "ProfileRegistry",
        "dataclass",
        "set_profile_registry",
    },
    # QR code generation is not required by ZUGFeRD or XRechnung specifications.
    "mcp_einvoicing_core.qr": {
        "generate_qr_png_base64",
    },
    # SchematronValidator is imported as the base class for DE's validator.
    # The remaining symbols are internal imports of schematron.py.
    "mcp_einvoicing_core.schematron": {
        "ABC",
        "BaseJSONValidator",
        "BaseStructuredValidator",
        "BaseXSDValidator",
        "Path",
        "SchematronValidator",
        "abstractmethod",
        "dataclass",
        "field",
        "safe_parser",
    },
    # DE provides its own XML helpers (mcp_einvoicing_de.utils.xml_utils) tailored to
    # CII and UBL namespaces; it imports only format_error and resolve_xml_input
    # from core. The remaining utilities are unused or have DE-local equivalents.
    "mcp_einvoicing_core.xml_utils": {
        "Any",
        "Decimal",
        "filter_empty_values",
        "format_amount",
        "format_quantity",
        "mark_untrusted",
        "mark_untrusted_fields",
        "safe_parser",
        "validate_date_iso",
        "validate_iban",
        "xml_element",
        "xml_escape",
        "xml_optional",
    },
}

# True  → EN 16931 family (ZUGFeRD, XRechnung, Peppol BIS, PINT-*):
#         primary invoice class must extend EN16931Invoice from core.
# See CLAUDE.md "Canonical invoice tree" for the full rule.
_IS_EN16931_FAMILY: bool = True

# The country package's primary invoice model class.
_PRIMARY_INVOICE_CLASS: tuple[str, str] = (
    "mcp_einvoicing_de.models.zugferd",
    "ZUGFeRDInvoice",
)

# DE package modules scanned for core symbol usage
_DE_MODULES: list[str] = [
    "mcp_einvoicing_de",
    "mcp_einvoicing_de.models.zugferd",
    "mcp_einvoicing_de.models.xrechnung",
    "mcp_einvoicing_de.validators.schematron",
    "mcp_einvoicing_de.validators.kosit",
    "mcp_einvoicing_de.tools.invoice_create",
    "mcp_einvoicing_de.tools.invoice_validate",
    "mcp_einvoicing_de.tools.invoice_parse",
    "mcp_einvoicing_de.tools.invoice_convert",
    "mcp_einvoicing_de.tools.peppol_check",
    "mcp_einvoicing_de.tools.tax_rules",
    "mcp_einvoicing_de.utils.xml_utils",
    "mcp_einvoicing_de.utils.pdf",
]

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


# ---------------------------------------------------------------------------
# CHECK 2 — Tool registry completeness
# ---------------------------------------------------------------------------

_REQUIRED_TOOL_CATEGORIES: dict[str, str] = {
    "invoice_create":   "Generate ZUGFeRD / XRechnung XML or PDF",
    "invoice_validate": "Validate against EN 16931 + KoSIT Schematron",
    "invoice_parse":    "Extract structured data from an invoice file",
    "invoice_convert":  "Convert between profiles or syntaxes",
    "peppol_check":     "Verify Peppol participant registration",
    "tax_rules":        "German VAT rules helper",
}


def _collect_registered_tools() -> set[str]:
    registered: set[str] = set()
    try:
        tool_modules = [
            ("mcp_einvoicing_de.tools.invoice_create",   "TOOL_INVOICE_CREATE"),
            ("mcp_einvoicing_de.tools.invoice_validate", "TOOL_INVOICE_VALIDATE"),
            ("mcp_einvoicing_de.tools.invoice_parse",    "TOOL_INVOICE_PARSE"),
            ("mcp_einvoicing_de.tools.invoice_convert",  "TOOL_INVOICE_CONVERT"),
            ("mcp_einvoicing_de.tools.peppol_check",     "TOOL_PEPPOL_CHECK"),
            ("mcp_einvoicing_de.tools.tax_rules",        "TOOL_TAX_RULES"),
        ]
        for mod_path, attr in tool_modules:
            mod, _ = _try_import(mod_path)
            if mod and hasattr(mod, attr):
                tool_obj = getattr(mod, attr)
                registered.add(tool_obj.name)
    except Exception:
        pass
    return registered


def run_check_2() -> CheckResult:
    """CHECK 2 — Tool registry completeness."""
    result = CheckResult(check_id="CHECK_2", name="Tool registry completeness")
    registered = _collect_registered_tools()

    for tool_name, description in _REQUIRED_TOOL_CATEGORIES.items():
        if tool_name in registered:
            result.findings.append(CheckFinding(
                check_id="CHECK_2", tag="[OK]", severity=SEVERITY_OK,
                symbol=tool_name,
                message=f"Tool '{tool_name}' is registered. ({description})",
            ))
        else:
            result.findings.append(CheckFinding(
                check_id="CHECK_2", tag="[MISSING_TOOL]", severity=SEVERITY_BLOCKING,
                symbol=tool_name,
                message=(
                    f"Required tool '{tool_name}' ({description}) is not registered "
                    "in the MCP server. Add it to server.py _ALL_TOOLS and _TOOL_HANDLERS."
                ),
            ))

    for tool_name in sorted(registered - set(_REQUIRED_TOOL_CATEGORIES)):
        result.findings.append(CheckFinding(
            check_id="CHECK_2", tag="[EXTRA]", severity=SEVERITY_OK,
            symbol=tool_name,
            message=f"Tool '{tool_name}' is registered but not in the required tool spec.",
        ))

    return result


# ---------------------------------------------------------------------------
# CHECK 3 — Model field alignment
# ---------------------------------------------------------------------------

# Fallback when mcp-einvoicing-core is not installed.
# Derived from EN16931Invoice fields that carry no default value (Pydantic required).
_CORE_MANDATORY_FIELDS_FALLBACK: dict[str, str] = {
    "profile":                   "GuidelineID / profile URN (BT-24)",
    "invoice_number":            "Invoice number (BT-1)",
    "invoice_date":              "Invoice issue date (BT-2)",
    "seller":                    "Seller / supplier (BG-4)",
    "buyer":                     "Buyer / customer (BG-7)",
    "sum_of_line_net_amounts":   "Sum of invoice line net amounts (BT-106)",
    "tax_exclusive_amount":      "Invoice total without VAT (BT-109)",
    "tax_total":                 "Total VAT amount (BT-110)",
    "tax_inclusive_amount":      "Invoice total with VAT (BT-112)",
    "amount_due":                "Amount due for payment (BT-115)",
    "tax_lines":                 "VAT breakdown lines (BG-23)",
}

# Fields present in core that are deprecated (update when core adds deprecation markers).
_DEPRECATED_CORE_FIELDS: set[str] = set()


def _get_mandatory_fields() -> dict[str, str]:
    """Return required EN16931Invoice fields derived from the installed core model."""
    core_mod, _ = _try_import("mcp_einvoicing_core.en16931")
    if core_mod is None:
        return dict(_CORE_MANDATORY_FIELDS_FALLBACK)
    en16931_cls = getattr(core_mod, "EN16931Invoice", None)
    if en16931_cls is None or not hasattr(en16931_cls, "model_fields"):
        return dict(_CORE_MANDATORY_FIELDS_FALLBACK)
    return {
        name: (fi.description or name)
        for name, fi in en16931_cls.model_fields.items()
        if fi.is_required()
    }


def run_check_3() -> CheckResult:
    """CHECK 3 — Model field alignment."""
    result = CheckResult(check_id="CHECK_3", name="Model field alignment")

    mod, err = _try_import("mcp_einvoicing_de.models.zugferd")
    if mod is None:
        result.skipped = True
        result.skip_reason = f"Could not import ZUGFeRD models: {err}"
        return result

    zugferd_cls = getattr(mod, "ZUGFeRDInvoice", None)
    if zugferd_cls is None:
        result.findings.append(CheckFinding(
            check_id="CHECK_3", tag="[MISSING]", severity=SEVERITY_BLOCKING,
            symbol="ZUGFeRDInvoice",
            message="ZUGFeRDInvoice class not found in mcp_einvoicing_de.models.zugferd.",
        ))
        return result

    model_fields = set(zugferd_cls.model_fields.keys())

    for field_name, description in _get_mandatory_fields().items():
        tag = "[OK]" if field_name in model_fields else "[FIELD_MISSING]"
        sev = SEVERITY_OK if field_name in model_fields else SEVERITY_BLOCKING
        result.findings.append(CheckFinding(
            check_id="CHECK_3", tag=tag, severity=sev,
            symbol=f"ZUGFeRDInvoice.{field_name}",
            message=(
                f"Mandatory field present. {description}"
                if field_name in model_fields
                else (
                    f"Mandatory EN 16931 field '{field_name}' ({description}) "
                    "is absent from ZUGFeRDInvoice."
                )
            ),
        ))

    for dep_field in _DEPRECATED_CORE_FIELDS:
        if dep_field in model_fields:
            result.findings.append(CheckFinding(
                check_id="CHECK_3", tag="[DEPRECATED_IN_USE]", severity=SEVERITY_WARNING,
                symbol=f"ZUGFeRDInvoice.{dep_field}",
                message=(
                    f"Field '{dep_field}' is marked deprecated in mcp-einvoicing-core "
                    "but is still present in ZUGFeRDInvoice."
                ),
            ))

    return result


# ---------------------------------------------------------------------------
# CHECK 5 — DE-specific structural checks
# ---------------------------------------------------------------------------

def run_check_5() -> CheckResult:
    """CHECK 5 — DE-specific structural and completeness checks."""
    result = CheckResult(check_id="CHECK_5", name="DE-specific structural checks")

    # 5a: Verify server.py exports _ALL_TOOLS and _TOOL_HANDLERS
    server_mod, err = _try_import("mcp_einvoicing_de.server")
    if server_mod is None:
        result.findings.append(CheckFinding(
            check_id="CHECK_5", tag="[MISSING]", severity=SEVERITY_BLOCKING,
            symbol="mcp_einvoicing_de.server",
            message=f"Could not import server module: {err}",
        ))
    else:
        for attr in ("_ALL_TOOLS", "_TOOL_HANDLERS", "main"):
            tag = "[OK]" if hasattr(server_mod, attr) else "[MISSING]"
            sev = SEVERITY_OK if hasattr(server_mod, attr) else SEVERITY_BLOCKING
            result.findings.append(CheckFinding(
                check_id="CHECK_5", tag=tag, severity=sev,
                symbol=f"server.{attr}",
                message=(
                    f"server.{attr} is present."
                    if hasattr(server_mod, attr)
                    else f"server.{attr} is missing — required for MCP server operation."
                ),
            ))

        # 5b: _ALL_TOOLS and _TOOL_HANDLERS must be in sync
        all_tools = getattr(server_mod, "_ALL_TOOLS", [])
        all_handlers = getattr(server_mod, "_TOOL_HANDLERS", {})
        tool_names_from_list = {t.name for t in all_tools}
        tool_names_from_handlers = set(all_handlers.keys())

        for name in sorted(tool_names_from_list - tool_names_from_handlers):
            result.findings.append(CheckFinding(
                check_id="CHECK_5", tag="[MISSING_HANDLER]", severity=SEVERITY_BLOCKING,
                symbol=f"_TOOL_HANDLERS[{name!r}]",
                message=f"Tool '{name}' is in _ALL_TOOLS but has no handler in _TOOL_HANDLERS.",
            ))
        for name in sorted(tool_names_from_handlers - tool_names_from_list):
            result.findings.append(CheckFinding(
                check_id="CHECK_5", tag="[MISSING_REGISTRATION]", severity=SEVERITY_WARNING,
                symbol=f"_ALL_TOOLS[{name!r}]",
                message=f"Handler '{name}' is in _TOOL_HANDLERS but not listed in _ALL_TOOLS.",
            ))
        if not (tool_names_from_list - tool_names_from_handlers) and not (
            tool_names_from_handlers - tool_names_from_list
        ):
            result.findings.append(CheckFinding(
                check_id="CHECK_5", tag="[OK]", severity=SEVERITY_OK,
                symbol="_ALL_TOOLS ↔ _TOOL_HANDLERS",
                message=f"All {len(all_tools)} tools have matching handlers.",
            ))

    # 5c: Verify ZUGFeRDProfile enum covers required profiles
    models_mod, _ = _try_import("mcp_einvoicing_de.models.zugferd")
    if models_mod:
        profile_cls = getattr(models_mod, "ZUGFeRDProfile", None)
        if profile_cls:
            required_profiles = {"MINIMUM", "BASIC_WL", "BASIC", "EN_16931", "EXTENDED", "XRECHNUNG"}
            actual_profiles = {p.name for p in profile_cls}
            for p in sorted(required_profiles):
                tag = "[OK]" if p in actual_profiles else "[MISSING_PROFILE]"
                sev = SEVERITY_OK if p in actual_profiles else SEVERITY_BLOCKING
                result.findings.append(CheckFinding(
                    check_id="CHECK_5", tag=tag, severity=sev,
                    symbol=f"ZUGFeRDProfile.{p}",
                    message=(
                        "Profile is defined."
                        if p in actual_profiles
                        else f"Required ZUGFeRD profile '{p}' is not defined in ZUGFeRDProfile enum."
                    ),
                ))

    # 5d: Verify XRechnung syntax variants are defined
    xr_mod, _ = _try_import("mcp_einvoicing_de.models.xrechnung")
    if xr_mod:
        syntax_cls = getattr(xr_mod, "XRechnungSyntax", None)
        if syntax_cls:
            required_syntaxes = {"CII", "UBL"}
            actual_syntaxes = {s.name for s in syntax_cls}
            for s in sorted(required_syntaxes):
                tag = "[OK]" if s in actual_syntaxes else "[MISSING_SYNTAX]"
                sev = SEVERITY_OK if s in actual_syntaxes else SEVERITY_BLOCKING
                result.findings.append(CheckFinding(
                    check_id="CHECK_5", tag=tag, severity=sev,
                    symbol=f"XRechnungSyntax.{s}",
                    message=(
                        "Syntax variant defined."
                        if s in actual_syntaxes
                        else f"Syntax variant '{s}' missing from XRechnungSyntax."
                    ),
                ))

    # 5e: Verify resources directory exists for Schematron stylesheets
    resources_dir = Path(__file__).parent.parent / "mcp_einvoicing_de" / "resources" / "schematron"
    if resources_dir.exists():
        xslt_files = list(resources_dir.glob("*.xslt"))
        result.findings.append(CheckFinding(
            check_id="CHECK_5", tag="[OK]", severity=SEVERITY_OK,
            symbol="resources/schematron/",
            message=f"Schematron resources directory found with {len(xslt_files)} XSLT file(s).",
        ))
    else:
        result.findings.append(CheckFinding(
            check_id="CHECK_5", tag="[MISSING_RESOURCES]", severity=SEVERITY_WARNING,
            symbol="resources/schematron/",
            message=(
                "Schematron XSLT stylesheets directory not found at "
                "mcp_einvoicing_de/resources/schematron/. "
                "Validation will fall back to NO-STYLESHEET mode. "
                "Bundle or download KoSIT + EN 16931 compiled XSLT files."
            ),
        ))

    return result


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def run_audit() -> AuditReport:
    """Execute all checks and return the aggregated AuditReport. No side effects."""
    report = make_report("mcp-einvoicing-de", _PYPROJECT)

    report.checks.append(run_check_core_coverage(
        package_name="mcp-einvoicing-de",
        package_modules=_DE_MODULES,
        intentional_overrides=_INTENTIONAL_OVERRIDES,
        is_en16931_family=_IS_EN16931_FAMILY,
        primary_invoice_class=_PRIMARY_INVOICE_CLASS,
    ))
    report.checks.append(run_check_2())
    report.checks.append(run_check_3())
    report.checks.append(run_check_version_compatibility(
        package_name="mcp-einvoicing-de",
        pyproject_path=_PYPROJECT,
    ))
    report.checks.append(run_check_5())

    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_audit_args(
        "Pre-publish audit: mcp-einvoicing-de vs mcp-einvoicing-core", argv
    )
    report = run_audit()

    output_path = Path(args.output) if args.output else Path("audit/report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    if not args.quiet:
        print(render_summary_table(report))
        print(f"\nJSON report written to: {output_path}")

    if args.fail_on == "never":
        return 0
    if args.fail_on == "warnings":
        return min(report.exit_code, 2)
    return 2 if report.total_blocking > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
