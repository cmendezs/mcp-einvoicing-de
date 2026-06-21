"""ZUGFeRD / XRechnung Schematron validator for mcp-einvoicing-de.

Extends mcp_einvoicing_core.SchematronValidator with a stylesheet key map
for the German rule sets.  All XSLT files are bundled inside the package
under ``mcp_einvoicing_de/rules/`` so local validation works after a plain
``pip install mcp-einvoicing-de`` without any extra download step.

Bundled rule sources and versions:
- ZUGFeRD / Factur-X profiles (MINIMUM, BASIC-WL, BASIC, EN16931, EXTENDED):
  FeRD / FNFE-MPE release package, Factur-X 1.08 (2025-12-04)
- EN 16931 UBL: KoSIT validator-configuration-xrechnung v2026-01-31
  (CEN Schematron Rules 1.3.15)
- XRechnung 3.0.2 CII/UBL: KoSIT validator-configuration-xrechnung v2026-01-31

Official rule sources:
- ZUGFeRD: https://www.ferd-net.de/standards/zugferd-2-0/index.html
- XRechnung: https://github.com/itplr-kosit/validator-configuration-xrechnung

XSLT 2.0 backend (DE-XSLT2-1):
The FeRD Factur-X stylesheets use XPath 2.0 constructs (``xs:decimal``,
``cast as``) that lxml / libxslt (XSLT 1.0 only) cannot compile. When the
optional ``saxonche`` extra is installed (``pip install
mcp-einvoicing-de[xslt2]``), the factory returns a Saxon-HE-backed validator
for those stylesheets; otherwise it raises a ``ValueError`` with a clear
remediation message.
"""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree
from mcp_einvoicing_core.schematron import (
    BaseStructuredValidator,
    ValidationMessage,
    ValidationResult,
)

# Re-export core types so that existing imports from this module still work
# (validators/kosit.py and tools/invoice_validate.py import these from here)
from mcp_einvoicing_core.schematron import (  # noqa: F401  (re-export)
    SchematronValidator as _CoreSchematronValidator,
)
from mcp_einvoicing_core.xml_utils import safe_parser

logger = logging.getLogger(__name__)

# Bundled rules directory — included in the wheel via hatchling's automatic
# package-data discovery (all files under mcp_einvoicing_de/ are included).
_RULES_DIR = Path(__file__).parent.parent / "rules"

# Maps stylesheet key → bundled XSLT file path.
# Keys mirror the ``_PROFILE_TO_STYLESHEET`` map in tools/invoice_validate.py.
_STYLESHEET_MAP: dict[str, Path] = {
    # FeRD / Factur-X 1.08 profile-specific compiled Schematron
    "zugferd_minimum_cii": _RULES_DIR / "FACTUR-X_MINIMUM.xslt",
    "zugferd_basicwl_cii": _RULES_DIR / "FACTUR-X_BASIC-WL.xslt",
    "zugferd_basic_cii":   _RULES_DIR / "FACTUR-X_BASIC.xslt",
    "en16931_cii":         _RULES_DIR / "FACTUR-X_EN16931.xslt",
    "zugferd_extended_cii": _RULES_DIR / "FACTUR-X_EXTENDED.xslt",
    # EN 16931 UBL (for XRechnung UBL base rules)
    "en16931_ubl":         _RULES_DIR / "EN16931-UBL-validation.xsl",
    # XRechnung 3.0.2 CIUS rules (CII and UBL)
    "xrechnung_cii":       _RULES_DIR / "XRechnung-CII-validation.xsl",
    "xrechnung_ubl":       _RULES_DIR / "XRechnung-UBL-validation.xsl",
}

_SVRL_NS = "http://purl.oclc.org/dsdl/svrl"
_SVRL_NSMAP = {"svrl": _SVRL_NS}


def _read_xslt_version(stylesheet_path: Path) -> str:
    """Return the value of the ``version`` attribute on the XSLT root element.

    Defaults to ``"1.0"`` when the file cannot be read or the attribute is missing.
    """
    try:
        root = etree.parse(str(stylesheet_path), safe_parser()).getroot()
    except (OSError, etree.XMLSyntaxError) as exc:
        logger.warning("Could not read XSLT version from %s: %s", stylesheet_path, exc)
        return "1.0"
    return root.get("version") or "1.0"


class SaxonSchematronValidator(BaseStructuredValidator):
    """XSLT 2.0 / 3.0 Schematron validator backed by Saxon-HE via ``saxonche``.

    Used for the FeRD Factur-X 1.08 stylesheets, which use ``xs:decimal`` /
    ``cast as`` constructs that libxslt cannot compile. Requires the optional
    ``saxonche`` extra.

    Subclasses of :class:`BaseStructuredValidator` must never raise from
    ``validate()``; XML parse and SVRL parse errors are returned as
    error-severity findings.
    """

    def __init__(self, stylesheet_path: Path | str) -> None:
        path = Path(stylesheet_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Schematron stylesheet not found: {path}. "
                "Reinstall the package to restore bundled rules."
            )
        try:
            from saxonche import PySaxonProcessor  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError(
                "Stylesheet "
                f"{path.name} uses XPath 2.0 constructs that require Saxon-HE. "
                "Install the optional extra with "
                "`pip install mcp-einvoicing-de[xslt2]`."
            ) from exc

        # PySaxonProcessor is created once per validator; it holds the compiled
        # XSLT executable, which is reused across validate() calls.
        self._proc = PySaxonProcessor(license=False)
        xslt_processor = self._proc.new_xslt30_processor()
        try:
            self._executable = xslt_processor.compile_stylesheet(stylesheet_file=str(path))
        except Exception as exc:
            raise ValueError(
                f"Failed to compile XSLT 2.0 stylesheet {path}: {exc}"
            ) from exc
        if self._executable is None:
            raise ValueError(
                f"Saxon returned no compiled executable for stylesheet {path}."
            )
        self._stylesheet_path = path

    def validate(
        self,
        document: bytes,
        *,
        profile: str = "",
        syntax: str = "",
    ) -> ValidationResult:
        try:
            xdm_input = self._proc.parse_xml(xml_text=document.decode("utf-8"))
        except Exception as exc:
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
                profile=profile,
                syntax=syntax,
            )

        try:
            svrl_text = self._executable.transform_to_string(xdm_node=xdm_input)
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationMessage(
                        severity="error",
                        rule_id="XSLT-RUNTIME",
                        location="/",
                        text=f"Saxon XSLT transform failed: {exc}",
                    )
                ],
                profile=profile,
                syntax=syntax,
            )

        result = self._parse_svrl(svrl_text or "")
        result.profile = profile
        result.syntax = syntax
        return result

    def _parse_svrl(self, svrl_text: str) -> ValidationResult:
        """Parse SVRL XML text into a ValidationResult mirroring core semantics."""
        errors: list[ValidationMessage] = []
        warnings: list[ValidationMessage] = []
        if not svrl_text.strip():
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

        try:
            svrl_root = etree.fromstring(svrl_text.encode("utf-8"), safe_parser())
        except etree.XMLSyntaxError as exc:
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationMessage(
                        severity="error",
                        rule_id="SVRL-PARSE",
                        location="/",
                        text=str(exc),
                    )
                ],
            )

        for failed in svrl_root.xpath("//svrl:failed-assert", namespaces=_SVRL_NSMAP):
            flag = (failed.get("flag") or "error").lower()
            rule_id = failed.get("id") or ""
            location = failed.get("location") or ""
            text_el = failed.find(f"{{{_SVRL_NS}}}text")
            text = (text_el.text or "").strip() if text_el is not None else ""

            msg = ValidationMessage(
                severity=flag, rule_id=rule_id, location=location, text=text
            )
            if flag in ("error", "fatal"):
                errors.append(msg)
            else:
                warnings.append(msg)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def SchematronValidator(stylesheet_key: str) -> BaseStructuredValidator:  # noqa: N802
    """Factory: return the right validator backend for a bundled stylesheet key.

    Reads the ``version`` attribute on the XSLT root and dispatches to the
    XSLT 1.0 backend in core for ``version="1.0"`` (KoSIT XRechnung / EN 16931
    UBL) or to :class:`SaxonSchematronValidator` for ``version="2.0"`` and
    later (FeRD Factur-X stylesheets).

    Args:
        stylesheet_key: One of the keys in ``_STYLESHEET_MAP``.

    Raises:
        ValueError:        If the key is unknown, or an XSLT 2.0 stylesheet
                           is requested without ``saxonche`` installed.
        FileNotFoundError: If the XSLT file is missing from the package
                           (reinstall to restore bundled rules).
    """
    stylesheet_path = _STYLESHEET_MAP.get(stylesheet_key)
    if stylesheet_path is None:
        raise ValueError(
            f"Unknown stylesheet key: {stylesheet_key!r}. "
            f"Valid keys: {sorted(_STYLESHEET_MAP)}"
        )

    version = _read_xslt_version(stylesheet_path)
    if version.startswith("1."):
        return _CoreSchematronValidator(stylesheet_path)
    return SaxonSchematronValidator(stylesheet_path)
