"""Local Schematron validation for ZUGFeRD and XRechnung.

Applies pre-compiled XSLT stylesheets derived from the official Schematron
rules provided by EN 16931 CEN and KoSIT (for XRechnung-specific BR-DE-* rules).

Official rule sources:
- EN 16931 CEN rules: [NEED: CEN GitLab URL for EN-16931 validation artefacts]
- KoSIT XRechnung rules: https://github.com/itplr-kosit/xrechnung-schematron
- KoSIT validation tool: https://github.com/itplr-kosit/validationtool

[NEED: confirm whether mcp-einvoicing-core already provides a SchematronValidator
base class that this should extend rather than re-implement]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Paths to compiled XSLT stylesheets (bundled with the package)
# [NEED: add actual XSLT files under mcp_einvoicing_de/resources/schematron/]
_RESOURCES_DIR = Path(__file__).parent.parent / "resources" / "schematron"

_STYLESHEET_MAP: dict[str, Path] = {
    # EN 16931 core rules (syntax-independent)
    "en16931_cii": _RESOURCES_DIR / "EN16931-CII-validation.xslt",
    "en16931_ubl": _RESOURCES_DIR / "EN16931-UBL-validation.xslt",
    # KoSIT XRechnung-specific BR-DE-* rules
    "xrechnung_cii": _RESOURCES_DIR / "XRechnung-CII-validation.xslt",
    "xrechnung_ubl": _RESOURCES_DIR / "XRechnung-UBL-validation.xslt",
}


@dataclass
class ValidationMessage:
    """Single validation finding returned by a Schematron rule."""

    severity: str  # "error" | "warning" | "info"
    rule_id: str  # e.g. "BR-DE-1", "BR-S-08"
    location: str  # XPath location in the invoice document
    text: str  # Human-readable message


@dataclass
class ValidationResult:
    """Aggregated result of a full Schematron validation run."""

    is_valid: bool
    errors: list[ValidationMessage] = field(default_factory=list)
    warnings: list[ValidationMessage] = field(default_factory=list)
    profile: str = ""
    syntax: str = ""

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "profile": self.profile,
            "syntax": self.syntax,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [vars(e) for e in self.errors],
            "warnings": [vars(w) for w in self.warnings],
        }


class SchematronValidator:
    """
    Apply Schematron rules to a ZUGFeRD or XRechnung XML document.

    Uses pre-compiled XSLT stylesheets (Skeleton Schematron) for performance.
    Stylesheet files must be present under mcp_einvoicing_de/resources/schematron/.

    [NEED: bundle actual compiled XSLT files or download them at first run]
    [NEED: verify if mcp-einvoicing-core exposes a base class to extend here]
    """

    def __init__(self, stylesheet_key: str) -> None:
        stylesheet_path = _STYLESHEET_MAP.get(stylesheet_key)
        if stylesheet_path is None:
            raise ValueError(
                f"Unknown stylesheet key: {stylesheet_key!r}. "
                f"Valid keys: {list(_STYLESHEET_MAP)}"
            )
        if not stylesheet_path.exists():
            raise FileNotFoundError(
                f"Schematron stylesheet not found: {stylesheet_path}. "
                "Run `mcp-einvoicing-de download-rules` to fetch official artefacts. "
                "[NEED: implement download-rules CLI subcommand]"
            )
        self._transform = etree.XSLT(etree.parse(str(stylesheet_path)))
        self._stylesheet_key = stylesheet_key

    def validate(self, xml_bytes: bytes) -> ValidationResult:
        """Validate *xml_bytes* and return a structured result."""
        try:
            doc = etree.fromstring(xml_bytes)
        except etree.XMLSyntaxError as exc:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationMessage(
                        severity="error",
                        rule_id="XML-PARSE",
                        location="/",
                        text=str(exc),
                    )
                ],
            )

        svrl_doc = self._transform(doc)
        return self._parse_svrl(svrl_doc)

    def _parse_svrl(self, svrl_doc: etree._XSLTResultTree) -> ValidationResult:
        """Parse SVRL (Schematron Validation Report Language) output."""
        # SVRL namespace: http://purl.oclc.org/dsdl/svrl
        ns = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
        errors: list[ValidationMessage] = []
        warnings: list[ValidationMessage] = []

        for failed in svrl_doc.xpath("//svrl:failed-assert", namespaces=ns):
            flag = failed.get("flag", "error").lower()
            rule_id = failed.get("id", "")
            location = failed.get("location", "")
            text_el = failed.find("svrl:text", ns)
            text = (text_el.text or "").strip() if text_el is not None else ""
            msg = ValidationMessage(severity=flag, rule_id=rule_id, location=location, text=text)
            if flag in ("error", "fatal"):
                errors.append(msg)
            else:
                warnings.append(msg)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            profile=self._stylesheet_key,
        )
