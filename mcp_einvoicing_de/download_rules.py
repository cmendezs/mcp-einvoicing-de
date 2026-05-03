"""Download Schematron artefacts for mcp-einvoicing-de.

Fetches the compiled XSLT stylesheets required by SchematronValidator from
their official sources and installs them under
mcp_einvoicing_de/resources/schematron/.

Official sources:
  EN 16931 CII/UBL rules: KoSIT validator configuration repository
    https://github.com/itplr-kosit/validator-configuration-xrechnung/releases
    [Unverified: confirm exact artefact URLs from the latest KoSIT release]

  XRechnung Schematron rules: KoSIT xrechnung-schematron repository
    https://github.com/itplr-kosit/xrechnung-schematron/releases
    [Unverified: confirm exact artefact URLs and ZIP internal paths]

Usage:
    mcp-einvoicing-de-download-rules [--overwrite]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp_einvoicing_core.download_rules import DownloadSpec, download_artefacts

_TARGET_DIR = Path(__file__).parent / "resources" / "schematron"

# ---------------------------------------------------------------------------
# Download specifications
# [Unverified: all URLs and zip_path values below require verification against
#  the current KoSIT release pages before production use.
#  Check https://github.com/itplr-kosit/xrechnung-schematron/releases and
#  https://github.com/itplr-kosit/validator-configuration-xrechnung/releases]
# ---------------------------------------------------------------------------

DOWNLOAD_SPECS: list[DownloadSpec] = [
    DownloadSpec(
        name="EN 16931 CII Schematron (compiled XSLT)",
        url=(
            "https://github.com/itplr-kosit/validator-configuration-xrechnung"
            "/releases/download/release-2024-11-15"
            "/validator-configuration-xrechnung_3.0.2_2024-11-15.zip"
        ),
        dest_filename="EN16931-CII-validation.xslt",
        zip_path=(
            "validator-configuration-xrechnung_3.0.2_2024-11-15"
            "/resources/xrechnung/3.0.2/schematron"
            "/EN16931-CII-validation.xslt"
        ),
    ),
    DownloadSpec(
        name="EN 16931 UBL Schematron (compiled XSLT)",
        url=(
            "https://github.com/itplr-kosit/validator-configuration-xrechnung"
            "/releases/download/release-2024-11-15"
            "/validator-configuration-xrechnung_3.0.2_2024-11-15.zip"
        ),
        dest_filename="EN16931-UBL-validation.xslt",
        zip_path=(
            "validator-configuration-xrechnung_3.0.2_2024-11-15"
            "/resources/xrechnung/3.0.2/schematron"
            "/EN16931-UBL-validation.xslt"
        ),
    ),
    DownloadSpec(
        name="XRechnung 3.x CII Schematron (compiled XSLT)",
        url=(
            "https://github.com/itplr-kosit/xrechnung-schematron"
            "/releases/download/release-2024-11-15"
            "/xrechnung-schematron-3.0.2_2024-11-15.zip"
        ),
        dest_filename="XRechnung-CII-validation.xslt",
        zip_path=(
            "xrechnung-schematron-3.0.2_2024-11-15"
            "/schematron/compiled/XRechnung-CII-validation.xslt"
        ),
    ),
    DownloadSpec(
        name="XRechnung 3.x UBL Schematron (compiled XSLT)",
        url=(
            "https://github.com/itplr-kosit/xrechnung-schematron"
            "/releases/download/release-2024-11-15"
            "/xrechnung-schematron-3.0.2_2024-11-15.zip"
        ),
        dest_filename="XRechnung-UBL-validation.xslt",
        zip_path=(
            "xrechnung-schematron-3.0.2_2024-11-15"
            "/schematron/compiled/XRechnung-UBL-validation.xslt"
        ),
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download Schematron XSLT artefacts for mcp-einvoicing-de.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Artefact sources:\n"
            "  KoSIT validator configuration: "
            "https://github.com/itplr-kosit/validator-configuration-xrechnung/releases\n"
            "  KoSIT XRechnung Schematron:     "
            "https://github.com/itplr-kosit/xrechnung-schematron/releases\n"
            "\n"
            "[Unverified: confirm artefact URLs match the current KoSIT release "
            "before relying on downloaded files for production validation.]"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download and overwrite existing files.",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=_TARGET_DIR,
        help=f"Directory to write artefacts into (default: {_TARGET_DIR}).",
    )
    args = parser.parse_args()

    print(f"Downloading ZUGFeRD / XRechnung Schematron artefacts to: {args.target_dir}")
    print()
    return download_artefacts(
        DOWNLOAD_SPECS,
        args.target_dir,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    sys.exit(main())
