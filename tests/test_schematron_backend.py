"""Tests for the SchematronValidator factory and XSLT 2.0 backend selection."""

from __future__ import annotations

import importlib.util

import pytest
from mcp_einvoicing_core.schematron import get_xslt_version

from mcp_einvoicing_de.validators.schematron import (
    _STYLESHEET_MAP,
    SaxonSchematronValidator,
    SchematronValidator,
)

_SAXON_AVAILABLE = importlib.util.find_spec("saxonche") is not None


class TestXsltVersionDetection:
    def test_all_bundled_stylesheets_are_xslt2(self) -> None:
        # Both the FeRD Factur-X compiled rules and the KoSIT
        # validator-configuration-xrechnung rules currently ship as XSLT 2.0.
        for key, path in _STYLESHEET_MAP.items():
            version = get_xslt_version(path)
            assert version.startswith(("2.", "3.")), (
                f"Expected XSLT 2.0+ for {key}, got version={version!r}"
            )


class TestFactoryDispatch:
    @pytest.mark.skipif(not _SAXON_AVAILABLE, reason="saxonche extra not installed")
    def test_factory_returns_saxon_for_all_bundled_keys(self) -> None:
        for key in _STYLESHEET_MAP:
            validator = SchematronValidator(key)
            assert isinstance(validator, SaxonSchematronValidator), (
                f"Expected Saxon backend for {key}, got {type(validator).__name__}"
            )

    def test_factory_rejects_unknown_key(self) -> None:
        with pytest.raises(ValueError, match="Unknown stylesheet key"):
            SchematronValidator("not_a_real_key")

    def test_factory_raises_import_error_without_saxonche(self, monkeypatch) -> None:
        """Simulate the optional [xslt2] extra not being installed.

        The factory now delegates to core's ``load_schematron_validator()``,
        which raises ``ImportError`` (not ``ValueError``) when ``saxonche`` is
        missing. ``tools/invoice_validate.py`` catches this specifically —
        this test guards that contract.
        """
        import sys

        monkeypatch.setitem(sys.modules, "saxonche", None)
        with pytest.raises(ImportError, match="mcp-einvoicing-core\\[xslt2\\]"):
            SchematronValidator("zugferd_minimum_cii")


@pytest.mark.skipif(not _SAXON_AVAILABLE, reason="saxonche extra not installed")
class TestSaxonValidatorBehaviour:
    def test_validates_minimal_cii_invoice(self, minimal_cii_xml: bytes) -> None:
        validator = SchematronValidator("zugferd_minimum_cii")
        result = validator.validate(minimal_cii_xml, profile="MINIMUM", syntax="CII")
        # The minimal_cii_xml fixture is intentionally barebones; the FeRD rules
        # will likely report many findings. The contract under test is that the
        # backend returns a ValidationResult without raising.
        assert hasattr(result, "is_valid")
        assert isinstance(result.errors, list)
