"""Tests for KoSIT validator response parsing (DE-LC-1)."""

from __future__ import annotations

from mcp_einvoicing_de.validators.kosit import KoSITValidator


class TestKoSITParseResponse:
    """Unit tests for _parse_response — no network calls required."""

    def _validator(self) -> KoSITValidator:
        return KoSITValidator(base_url="http://localhost:8080/api/v1/validate")

    def test_valid_response_with_no_violations(self) -> None:
        data = {"valid": True, "violations": [], "notices": []}
        result = self._validator()._parse_response(data)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_response_with_error_violation(self) -> None:
        data = {
            "valid": False,
            "violations": [
                {
                    "type": "error",
                    "context": "/Invoice/BuyerReference",
                    "test": "BR-DE-15",
                    "text": "[BR-DE-15] Buyer reference fehlt.",
                }
            ],
        }
        result = self._validator()._parse_response(data)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].location == "/Invoice/BuyerReference"
        assert "BR-DE-15" in result.errors[0].rule_id
        assert "Buyer reference" in result.errors[0].text

    def test_warning_violation_goes_to_warnings(self) -> None:
        data = {
            "valid": True,
            "violations": [
                {
                    "type": "warning",
                    "context": "/Invoice",
                    "test": "some-warning-rule",
                    "text": "Advisory message.",
                }
            ],
        }
        result = self._validator()._parse_response(data)
        assert result.is_valid is True
        assert result.errors == []
        assert len(result.warnings) == 1

    def test_missing_valid_key_fails_safe(self) -> None:
        """If 'valid' key is absent but violations are empty, must NOT return True."""
        data = {"violations": []}
        result = self._validator()._parse_response(data)
        assert result.is_valid is False

    def test_unrecognised_response_shape_fails_safe(self) -> None:
        """Response with neither 'valid' nor 'violations' must return is_valid=False."""
        data = {"status": "ok", "result": "pass"}
        result = self._validator()._parse_response(data)
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "KOSIT-UNEXPECTED-RESPONSE" in result.errors[0].rule_id

    def test_information_type_goes_to_warnings(self) -> None:
        data = {
            "valid": True,
            "violations": [
                {
                    "type": "information",
                    "context": "/",
                    "test": "info-rule",
                    "text": "Informational notice.",
                }
            ],
        }
        result = self._validator()._parse_response(data)
        assert len(result.warnings) == 1
        assert result.errors == []
