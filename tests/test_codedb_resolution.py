"""DE-GAP-1: bundled FeRD Factur-X stylesheets must resolve their codedb.

Each of the 5 profile-specific FACTUR-X_*.xslt stylesheets calls
``document('FACTUR-X_<PROFILE>_codedb.xml')`` (a relative URI resolved by
Saxon against the stylesheet's own directory) to check UN/CEFACT code-list
membership (currencies, units of measure, tax categories, etc.). The
codedb.xml sidecar files were missing from ``rules/`` even though the
stylesheets were bundled there, so every real-invoice validation failed with
a Saxon FODC0002 I/O error before this fix.
"""

from __future__ import annotations

import glob
import importlib.util
from pathlib import Path

import pytest

from mcp_einvoicing_de.validators.schematron import SchematronValidator

_SAXON_AVAILABLE = importlib.util.find_spec("saxonche") is not None

_RULES_DIR = Path(__file__).parent.parent / "src" / "mcp_einvoicing_de" / "rules"
_SPECS_EXAMPLES = Path(__file__).parent.parent / "specs" / "examples" / "zugferd"

# stylesheet key -> (expected codedb filename, examples subdirectory)
_FERD_PROFILES = {
    "zugferd_minimum_cii": ("FACTUR-X_MINIMUM_codedb.xml", "MINIMUM"),
    "zugferd_basicwl_cii": ("FACTUR-X_BASIC-WL_codedb.xml", "BASIC_WL"),
    "zugferd_basic_cii": ("FACTUR-X_BASIC_codedb.xml", "BASIC"),
    "en16931_cii": ("FACTUR-X_EN16931_codedb.xml", "EN16931"),
    "zugferd_extended_cii": ("FACTUR-X_EXTENDED_codedb.xml", "EXTENDED"),
}


class TestCodedbFilesBundled:
    @pytest.mark.parametrize("codedb_name", [name for name, _ in _FERD_PROFILES.values()])
    def test_codedb_file_present_in_rules_dir(self, codedb_name: str) -> None:
        path = _RULES_DIR / codedb_name
        assert path.is_file(), f"Missing bundled codedb file: {path}"
        assert path.stat().st_size > 0


class TestCodedbResolvesWithoutIOError:
    """Regression guard: Saxon must not raise FODC0002 against real samples."""

    @pytest.mark.skipif(not _SAXON_AVAILABLE, reason="saxonche extra not installed")
    @pytest.mark.parametrize("stylesheet_key", list(_FERD_PROFILES))
    def test_real_sample_validates_without_io_error(self, stylesheet_key: str) -> None:
        codedb_name, examples_dir = _FERD_PROFILES[stylesheet_key]
        samples = sorted(glob.glob(str(_SPECS_EXAMPLES / examples_dir / "*.xml")))
        assert samples, f"No reference samples found under {_SPECS_EXAMPLES / examples_dir}"

        validator = SchematronValidator(stylesheet_key)
        xml_bytes = Path(samples[0]).read_bytes()
        result = validator.validate(xml_bytes)

        io_errors = [
            e
            for e in (*result.errors, *result.warnings)
            if "FODC0002" in e.text or "FileNotFoundException" in e.text or codedb_name in e.text
        ]
        assert io_errors == [], f"{stylesheet_key}: unexpected I/O errors: {io_errors}"
