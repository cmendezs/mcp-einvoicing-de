"""DE-LC-2: KoSITValidator must not have an implicit default endpoint."""

from __future__ import annotations

import pytest

from mcp_einvoicing_de.validators.kosit import KoSITValidator


class TestKoSITNoImplicitDefault:
    def test_missing_url_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            KoSITValidator()  # type: ignore[call-arg]

    def test_explicit_sentinel_url_constructs(self) -> None:
        validator = KoSITValidator(KoSITValidator._UNVERIFIED_DEFAULT_KOSIT_URL)
        assert validator is not None

    def test_explicit_localhost_url_constructs(self) -> None:
        validator = KoSITValidator("http://localhost:8080/api/v1/validate")
        assert validator is not None
