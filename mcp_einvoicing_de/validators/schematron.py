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
"""

from __future__ import annotations

import logging
from pathlib import Path

# Re-export core types so that existing imports from this module still work
# (validators/kosit.py and tools/invoice_validate.py import these from here)
from mcp_einvoicing_core.schematron import (  # noqa: F401  (re-export)
    SchematronValidator as _CoreSchematronValidator,
)
from mcp_einvoicing_core.schematron import ValidationMessage, ValidationResult  # noqa: F401

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


class SchematronValidator(_CoreSchematronValidator):
    """ZUGFeRD / XRechnung Schematron validator.

    Resolves a stylesheet key to the corresponding bundled XSLT file and
    delegates all XSLT execution and SVRL parsing to the core base class.

    Args:
        stylesheet_key: One of the keys in ``_STYLESHEET_MAP`` —
            ``zugferd_minimum_cii``, ``zugferd_basicwl_cii``,
            ``zugferd_basic_cii``, ``en16931_cii``, ``zugferd_extended_cii``,
            ``en16931_ubl``, ``xrechnung_cii``, ``xrechnung_ubl``.

    Raises:
        ValueError:        If the key is not in _STYLESHEET_MAP.
        FileNotFoundError: If the XSLT file is missing from the package
                           (re-install the package to restore bundled rules).
    """

    def __init__(self, stylesheet_key: str) -> None:
        stylesheet_path = _STYLESHEET_MAP.get(stylesheet_key)
        if stylesheet_path is None:
            raise ValueError(
                f"Unknown stylesheet key: {stylesheet_key!r}. "
                f"Valid keys: {sorted(_STYLESHEET_MAP)}"
            )
        super().__init__(stylesheet_path)
