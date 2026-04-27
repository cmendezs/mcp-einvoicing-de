"""KoSIT online validator integration.

Wraps the KoSIT Validierungstool REST API for remote validation of
XRechnung invoices. This is the official German government validator.

Official tool: https://github.com/itplr-kosit/validationtool
Online demo: [NEED: confirm whether KoSIT provides a public REST endpoint]
Self-hosted: docker pull ghcr.io/itplr-kosit/validationtool
[NEED: official Docker image name and run instructions]
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from mcp_einvoicing_de.validators.schematron import ValidationMessage, ValidationResult

logger = logging.getLogger(__name__)

_DEFAULT_KOSIT_URL = os.environ.get(
    "EINVOICING_DE_KOSIT_VALIDATOR_URL",
    # [NEED: confirm KoSIT self-hosted default port and path]
    "http://localhost:8080/api/v1/validate",
)


class KoSITValidator:
    """
    Remote validator using the KoSIT Validierungstool REST API.

    Prefer this over local Schematron for production use — the KoSIT tool
    applies the full suite of XRechnung rules including those that require
    multi-document context.

    [NEED: confirm KoSIT API request/response schema]
    [NEED: confirm whether mcp-einvoicing-core provides a RemoteValidatorBase]
    """

    def __init__(self, base_url: str = _DEFAULT_KOSIT_URL, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
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
