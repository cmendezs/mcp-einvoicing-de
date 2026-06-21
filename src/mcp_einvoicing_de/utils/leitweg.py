"""Leitweg-ID format and check-digit validator.

Leitweg-ID is the routing identifier mandatory for B2G invoices in Germany
(XRechnung, BT-10 / Buyer reference field).

Format: ``<Verwaltungsebene>-[<Instanzkennzeichen>-]<Prüfziffer>``

    Verwaltungsebene: 1–12 decimal digits
    Instanzkennzeichen: 0–30 uppercase alphanumeric characters (may be absent)
    Prüfziffer: exactly 2 decimal digits (ISO 7064 MOD 97-10 check)

Examples::

    04011000-12345-03   valid (Verwaltungsebene + Instanzkennzeichen + check)
    991-01-03           valid (Verwaltungsebene + Instanzkennzeichen + check)

Authority: KoSIT — https://www.xoev.de/publikationen-2316
Check-digit algorithm: ISO 7064 MOD 97-10 (same family as IBAN).

[Inference: algorithm derived from ISO 7064 MOD 97-10 applied to the full
Leitweg-ID string (hyphens stripped, letters expanded A=10 … Z=35);
remainder mod 97 must equal 1. Verified against known-valid examples.]
"""

from __future__ import annotations

import re

# Pattern per KoSIT Leitweg-ID specification:
#   1–12 decimal digits (Verwaltungsebene)
#   followed by 1 or 2 hyphen-separated alphanumeric segments (case-insensitive)
#   ending with a hyphen and exactly 2 decimal digits (Prüfziffer)
_LEITWEG_PATTERN = re.compile(
    r"^[0-9]{1,12}(-[A-Za-z0-9]{1,30}){0,1}-[0-9]{2}$"
)


def _mod97(s: str) -> int:
    """ISO 7064 MOD 97-10: expand letters (A=10 … Z=35), compute mod 97."""
    digits = ""
    for ch in s.upper():
        if ch.isdigit():
            digits += ch
        elif ch.isalpha():
            digits += str(ord(ch) - 55)  # A→10, B→11, …, Z→35
    return int(digits) % 97


def validate_leitweg_id(value: str) -> str:
    """Validate Leitweg-ID format and ISO 7064 MOD 97-10 check digit.

    Args:
        value: The Leitweg-ID string to validate.

    Returns:
        The unchanged *value* if it is valid.

    Raises:
        ValueError: If the format is wrong or the check digit is invalid.

    [Inference: mod-97 algorithm matches ISO 7064 MOD 97-10; strip hyphens,
    expand letters, verify numeric_value mod 97 == 1.]
    """
    if not _LEITWEG_PATTERN.match(value):
        raise ValueError(
            f"Leitweg-ID {value!r} does not match the required format "
            r"'[0-9]{1,12}(-[A-Z0-9]{1,30})?-[0-9]{2}'. "
            "Expected: <Verwaltungsebene>[-<Instanzkennzeichen>]-<Prüfziffer>."
        )
    stripped = value.replace("-", "")
    if _mod97(stripped) != 1:
        raise ValueError(
            f"Leitweg-ID {value!r} has an invalid check digit "
            "(ISO 7064 MOD 97-10 remainder must equal 1)."
        )
    return value


def looks_like_leitweg_id(value: str) -> bool:
    """Return True if *value* matches the Leitweg-ID format pattern.

    Used to decide whether to apply the check-digit validation to a
    ``buyer_reference`` field that may legitimately hold non-Leitweg-ID
    buyer references (purchase order numbers, etc.).
    """
    return bool(_LEITWEG_PATTERN.match(value))
