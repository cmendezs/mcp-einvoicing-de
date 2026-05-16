"""KoSIT online validator integration.

Wraps the KoSIT Validierungstool REST API for remote validation of
XRechnung invoices. This is the official German government validator.

Official tool: https://github.com/itplr-kosit/validationtool
Self-hosted: docker pull ghcr.io/itplr-kosit/validationtool
[NEED: confirm KoSIT official Docker image name and recommended run instructions]

Security: the URL is validated at construction time. Plain HTTP is only
allowed for localhost; all non-localhost targets must use HTTPS.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp_einvoicing_core.exceptions import PlatformError
from mcp_einvoicing_core.schematron import ValidationMessage, ValidationResult

logger = logging.getLogger(__name__)

# Known KoSIT self-hosted and government hostnames.  Update when new official
# endpoints are published.  Extend via EINVOICING_KOSIT_ALLOWLIST (comma-separated).
_KOSIT_ALLOWLIST_DEFAULT: frozenset[str] = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "validationtool",        # common docker-compose service name
    "kosit-validator",       # alternative docker-compose service name
})

_DEFAULT_KOSIT_URL = os.environ.get(
    "EINVOICING_DE_KOSIT_VALIDATOR_URL",
    # Localhost default — must switch to https:// for remote/production endpoints.
    "http://localhost:8080/api/v1/validate",
)


def _validate_kosit_url(url: str) -> str:
    """Validate and return the KoSIT URL, or raise PlatformError.

    Rules:
    - Must use ``https://`` unless the host is localhost / 127.0.0.1 / ::1.
    - Host must be in the built-in allowlist or ``EINVOICING_KOSIT_ALLOWLIST``.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    scheme = parsed.scheme.lower()

    extra_hosts = frozenset(
        h.strip().lower()
        for h in os.environ.get("EINVOICING_KOSIT_ALLOWLIST", "").split(",")
        if h.strip()
    )
    allowed_hosts = _KOSIT_ALLOWLIST_DEFAULT | extra_hosts

    is_localhost = host in {"localhost", "127.0.0.1", "::1"}

    if scheme == "http" and not is_localhost:
        raise PlatformError(
            status_code=0,
            message=(
                f"KoSIT validator URL uses plain HTTP for non-localhost host {host!r}. "
                "Set EINVOICING_DE_KOSIT_VALIDATOR_URL to an https:// URL. "
                "Plain HTTP is only allowed for localhost."
            ),
        )
    if scheme not in ("http", "https"):
        raise PlatformError(
            status_code=0,
            message=f"KoSIT validator URL has unsupported scheme {scheme!r}. Use https://.",
        )
    if host not in allowed_hosts:
        raise PlatformError(
            status_code=0,
            message=(
                f"KoSIT validator host {host!r} is not in the allowlist. "
                "Add it to EINVOICING_KOSIT_ALLOWLIST if this is a trusted endpoint."
            ),
        )
    return url


class KoSITValidator:
    """Remote validator using the KoSIT Validierungstool REST API.

    Prefer this over local Schematron for production use — the KoSIT tool
    applies the full suite of XRechnung rules including those that require
    multi-document context.

    [NEED: confirm KoSIT API request/response schema]
    [NEED: confirm whether mcp-einvoicing-core provides a RemoteValidatorBase]
    """

    def __init__(self, base_url: str = _DEFAULT_KOSIT_URL, timeout: float = 30.0) -> None:
        self._base_url = _validate_kosit_url(base_url).rstrip("/")
        self._timeout = timeout

    async def validate(self, xml_bytes: bytes, filename: str = "invoice.xml") -> ValidationResult:
        """
        Submit *xml_bytes* to the KoSIT validator and return structured results.

        [NEED: confirm multipart field names expected by KoSIT REST API]
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._base_url,
                    files={"file": (filename, xml_bytes, "application/xml")},
                )
                response.raise_for_status()
                return self._parse_response(response.json())
        except httpx.HTTPError as exc:
            logger.error("KoSIT validator HTTP error: %s", exc)
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationMessage(
                        severity="error",
                        rule_id="KOSIT-HTTP",
                        location="/",
                        text=f"KoSIT validator unreachable: {exc}",
                    )
                ],
            )

    def _parse_response(self, data: dict[str, Any]) -> ValidationResult:
        """
        Parse KoSIT JSON response into ValidationResult.

        [NEED: actual KoSIT response JSON schema to implement this correctly]
        """
        # TODO: implement once KoSIT REST API schema is confirmed
        errors: list[ValidationMessage] = []
        warnings: list[ValidationMessage] = []

        for item in data.get("reports", []):
            for finding in item.get("findings", []):
                msg = ValidationMessage(
                    severity=finding.get("severity", "error").lower(),
                    rule_id=finding.get("ruleId", ""),
                    location=finding.get("location", ""),
                    text=finding.get("message", ""),
                )
                if msg.severity in ("error", "fatal"):
                    errors.append(msg)
                else:
                    warnings.append(msg)

        return ValidationResult(
            is_valid=data.get("valid", len(errors) == 0),
            errors=errors,
            warnings=warnings,
        )
