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
``cast as``) that lxml / libxslt (XSLT 1.0 only) cannot compile. Version
detection and backend dispatch are delegated to core's
``load_schematron_validator()``, which returns
``mcp_einvoicing_core.schematron.SaxonSchematronValidator`` (Saxon-HE via the
optional ``saxonche`` extra: ``pip install mcp-einvoicing-de[xslt2]``) for
XSLT 2.0+ stylesheets, or raises ``ImportError`` with a remediation message
when the extra is missing.
"""

from __future__ import annotations

from pathlib import Path

from mcp_einvoicing_core.schematron import (
    BaseStructuredValidator,
    SaxonSchematronValidator,
    ValidationMessage,
    ValidationResult,
    load_schematron_validator,
)

# Re-export core types so that existing imports from this module still work
# (validators/kosit.py and tools/invoice_validate.py import these from here)
from mcp_einvoicing_core.schematron import (  # noqa: F401  (re-export)
    SchematronValidator as _CoreSchematronValidator,
)

__all__ = [
    "SchematronValidator",
    "SaxonSchematronValidator",
    "ValidationMessage",
    "ValidationResult",
]

# Bundled rules directory — included in the wheel via hatchling's automatic
# package-data discovery (all files under mcp_einvoicing_de/ are included).
_RULES_DIR = Path(__file__).parent.parent / "rules"

# Maps stylesheet key → bundled XSLT file path.
# Keys mirror the ``_PROFILE_TO_STYLESHEET`` map in tools/invoice_validate.py.
_STYLESHEET_MAP: dict[str, Path] = {
    # FeRD / Factur-X 1.08 profile-specific compiled Schematron
    "zugferd_minimum_cii": _RULES_DIR / "FACTUR-X_MINIMUM.xslt",
    "zugferd_basicwl_cii": _RULES_DIR / "FACTUR-X_BASIC-WL.xslt",
    "zugferd_basic_cii": _RULES_DIR / "FACTUR-X_BASIC.xslt",
    "en16931_cii": _RULES_DIR / "FACTUR-X_EN16931.xslt",
    "zugferd_extended_cii": _RULES_DIR / "FACTUR-X_EXTENDED.xslt",
    # EN 16931 UBL (for XRechnung UBL base rules)
    "en16931_ubl": _RULES_DIR / "EN16931-UBL-validation.xsl",
    # XRechnung 3.0.2 CIUS rules (CII and UBL)
    "xrechnung_cii": _RULES_DIR / "XRechnung-CII-validation.xsl",
    "xrechnung_ubl": _RULES_DIR / "XRechnung-UBL-validation.xsl",
}


def SchematronValidator(stylesheet_key: str) -> BaseStructuredValidator:  # noqa: N802
    """Factory: return the right validator backend for a bundled stylesheet key.

    Delegates version detection and backend dispatch to core's
    ``load_schematron_validator()``: XSLT 1.0 stylesheets (KoSIT XRechnung /
    EN 16931 UBL base rules) get the lxml/libxslt-backed
    ``SchematronValidator``; XSLT 2.0+ stylesheets (FeRD Factur-X) get
    ``SaxonSchematronValidator`` (Saxon-HE).

    Args:
        stylesheet_key: One of the keys in ``_STYLESHEET_MAP``.

    Raises:
        ValueError:        If the key is unknown, or Saxon cannot compile an
                           XSLT 2.0+ stylesheet.
        FileNotFoundError: If the XSLT file is missing from the package
                           (reinstall to restore bundled rules).
        ImportError:       If an XSLT 2.0+ stylesheet is requested without
                           the optional ``saxonche`` extra installed.
    """
    stylesheet_path = _STYLESHEET_MAP.get(stylesheet_key)
    if stylesheet_path is None:
        raise ValueError(
            f"Unknown stylesheet key: {stylesheet_key!r}. Valid keys: {sorted(_STYLESHEET_MAP)}"
        )
    return load_schematron_validator(stylesheet_path)
