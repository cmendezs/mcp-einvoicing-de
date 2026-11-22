"""DE-LC-2: KoSITValidator must not have an implicit default endpoint."""

from __future__ import annotations

import pytest

from mcp_einvoicing_de.validators.kosit import KoSITValidator, configured_kosit_url


class TestKoSITNoImplicitDefault:
    def test_missing_url_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            KoSITValidator()  # type: ignore[call-arg]

    def test_no_built_in_default_url_attribute(self) -> None:
        assert not hasattr(KoSITValidator, "_UNVERIFIED_DEFAULT_KOSIT_URL")

    def test_configured_url_is_none_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EINVOICING_DE_KOSIT_VALIDATOR_URL", raising=False)
        assert configured_kosit_url() is None

    def test_configured_url_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EINVOICING_DE_KOSIT_VALIDATOR_URL", " http://localhost:8080/x ")
        assert configured_kosit_url() == "http://localhost:8080/x"

    def test_explicit_localhost_url_constructs(self) -> None:
        validator = KoSITValidator("http://localhost:8080/api/v1/validate")
        assert validator is not None
