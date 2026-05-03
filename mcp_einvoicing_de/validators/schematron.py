"""ZUGFeRD / XRechnung Schematron validator for mcp-einvoicing-de.

Extends mcp_einvoicing_core.SchematronValidator with a stylesheet key map
for the German rule sets (EN 16931 core rules + KoSIT XRechnung BR-DE-*).

The XSLT execution and SVRL parsing are handled by the core base class.
This module only maintains the mapping from DE-specific key names to the
bundled stylesheet file paths.

Download the stylesheet files with:
    mcp-einvoicing-de-download-rules

Official rule sources:
- EN 16931 CII/UBL: https://github.com/itplr-kosit/validator-configuration-xrechnung
  [Unverified: confirm exact artefact URLs from KoSIT release page]
- XRechnung Schematron: https://github.com/itplr-kosit/xrechnung-schematron/releases
  [Unverified: confirm file names inside the release ZIP]
"""

from __future__ import annotations

import logging
from pathlib import Path

# Re-export core types so that existing imports from this module still work
# (validators/kosit.py and tools/invoice_validate.py import these from here)
from mcp_einvoicing_core.schematron import (  # noqa: F401  (re-export)
    SchematronValidator as _CoreSchematronValidator,
    ValidationMessage,
    ValidationResult,
)

logger = logging.getLogger(__name__)

_RESOURCES_DIR = Path(__file__).parent.parent / "resources" / "schematron"

# Maps stylesheet key → compiled XSLT file path
_STYLESHEET_MAP: dict[str, Path] = {
    "en16931_cii": _RESOURCES_DIR / "EN16931-CII-validation.xslt",
    "en16931_ubl": _RESOURCES_DIR / "EN16931-UBL-validation.xslt",
    "xrechnung_cii": _RESOURCES_DIR / "XRechnung-CII-validation.xslt",
    "xrechnung_ubl": _RESOURCES_DIR / "XRechnung-UBL-validation.xslt",
}


class SchematronValidator(_CoreSchematronValidator):
    """ZUGFeRD / XRechnung Schematron validator.

    Resolves a stylesheet key to the corresponding bundled XSLT file and
    delegates all XSLT execution and SVRL parsing to the core base class.

    Args:
        stylesheet_key: One of "en16931_cii", "en16931_ubl",
                        "xrechnung_cii", "xrechnung_ubl".

    Raises:
        ValueError:      If the key is not in _STYLESHEET_MAP.
        FileNotFoundError: If the XSLT file is absent (run download-rules).
    """

    def __init__(self, stylesheet_key: str) -> None:
        stylesheet_path = _STYLESHEET_MAP.get(stylesheet_key)
        if stylesheet_path is None:
            raise ValueError(
                f"Unknown stylesheet key: {stylesheet_key!r}. "
                f"Valid keys: {sorted(_STYLESHEET_MAP)}"
            )
        # Core __init__ checks existence and raises FileNotFoundError with a
        # helpful message that already mentions the download-rules command.
        super().__init__(stylesheet_path)
