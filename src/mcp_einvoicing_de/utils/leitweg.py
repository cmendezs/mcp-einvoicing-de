"""Leitweg-ID format and check-digit validator.

Delegates to ``mcp_einvoicing_core.routing.RoutingIdentifier.validate_de_leitweg``
for the actual validation logic. This module preserves the local API
(``validate_leitweg_id`` raising ``ValueError``) so existing DE imports
continue to work without changes.

Leitweg-ID is the routing identifier mandatory for B2G invoices in Germany
(XRechnung, BT-10 / Buyer reference field).

Authority: KoSIT, https://www.xoev.de/publikationen-2316
"""

from __future__ import annotations

import re

from mcp_einvoicing_core.routing import RoutingIdentifier

_LEITWEG_PATTERN = re.compile(r"^[0-9]{1,12}(-[A-Za-z0-9]{1,30}){0,1}-[0-9]{2}$")


def validate_leitweg_id(value: str) -> str:
    """Validate Leitweg-ID format and ISO 7064 MOD 97-10 check digit.

    Args:
        value: The Leitweg-ID string to validate.

    Returns:
        The unchanged *value* if it is valid.

    Raises:
        ValueError: If the format is wrong or the check digit is invalid.
    """
    result = RoutingIdentifier.validate_de_leitweg(value)
    if not result.valid:
        raise ValueError(result.error)
    return result.normalized_value


def looks_like_leitweg_id(value: str) -> bool:
    """Return True if *value* matches the Leitweg-ID format pattern.

    Used to decide whether to apply the check-digit validation to a
    ``buyer_reference`` field that may legitimately hold non-Leitweg-ID
    buyer references (purchase order numbers, etc.).
    """
    return bool(_LEITWEG_PATTERN.match(value))
