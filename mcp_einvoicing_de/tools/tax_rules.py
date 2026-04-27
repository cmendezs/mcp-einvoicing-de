"""MCP tool: tax_rules — German VAT rules helper.

Provides structured information about:
- German VAT rates (Regelsteuersatz 19%, ermäßigter Steuersatz 7%)
- VAT category codes (EN 16931 / UNCL5305 + German specifics)
- Reverse charge rules under §13b UStG
- Zero-rate and exemption rules (§4 UStG)
- Intra-community supply rules
- Common exemption reason codes (VATEX)

Legal references:
- Umsatzsteuergesetz (UStG): [NEED: link to current consolidated UStG text]
- BMF circulars on e-invoicing: [NEED: link to relevant BMF circulars]
- EN 16931-1:2017 Annex — VAT category codes

[NEED: verify current rates — rates may change; this is data as of 2025-01]
[NEED: verify if mcp-einvoicing-core provides a tax_rules base or registry]
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Current German VAT rates (as of 2025-01-01)
# [NEED: verify — temporary COVID reductions and construction sector changes]
_GERMAN_VAT_RATES: dict[str, Any] = {
    "S_19": {
        "category": "S",
        "rate_percent": 19,
        "name_de": "Regelsteuersatz",
        "name_en": "Standard rate",
        "applies_to": "Most goods and services not otherwise specified",
        "legal_basis": "§12 Abs. 1 UStG",
    },
    "AA_7": {
        "category": "AA",
        "rate_percent": 7,
        "name_de": "Ermäßigter Steuersatz",
        "name_en": "Reduced rate",
        "applies_to": (
            "Food (non-restaurant), books, newspapers, cultural services, "
            "public transport, hotel accommodation (since 2010)"
        ),
        "legal_basis": "§12 Abs. 2 UStG",
    },
}

_REVERSE_CHARGE_CASES: list[dict[str, Any]] = [
    {
        "paragraph": "§13b Abs. 2 Nr. 1 UStG",
        "description_de": "Werklieferungen und sonstige Leistungen eines im Ausland ansässigen Unternehmers",
        "description_en": "Supply of works and services by a foreign entrepreneur",
        "vatex_code": "VATEX-EU-AE",
        "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)",
    },
    {
        "paragraph": "§13b Abs. 2 Nr. 4 UStG",
        "description_de": "Lieferungen von Grundstücken",
        "description_en": "Supplies of real estate",
        "vatex_code": "VATEX-EU-AE",
        "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)",
    },
    {
        "paragraph": "§13b Abs. 2 Nr. 5 UStG",
        "description_de": "Bauleistungen (Bauträger-Regelung)",
        "description_en": "Construction services (building contractor rule)",
        "vatex_code": "VATEX-EU-AE",
        "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)",
        # [NEED: verify current BMF position on Bauleistungen after 2023 ruling]
    },
    {
        "paragraph": "§13b Abs. 2 Nr. 7 UStG",
        "description_de": "Lieferungen von Schrott und Altmaterialien",
        "description_en": "Supplies of scrap metal and recycled materials",
        "vatex_code": "VATEX-EU-AE",
        "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)",
    },
    {
        "paragraph": "§13b Abs. 2 Nr. 12 UStG",
        "description_de": "Lieferungen von Gas, Elektrizität, Wärme, Kälte",
        "description_en": "Supplies of gas, electricity, heat, cooling",
        "vatex_code": "VATEX-EU-AE",
        "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)",
        # [NEED: verify whether energy supplies are still in §13b after 2024 changes]
    },
]

_EXEMPTIONS: list[dict[str, Any]] = [
    {
        "paragraph": "§4 Nr. 1a UStG",
        "category": "G",
        "description_en": "Export outside EU",
        "vatex_code": "VATEX-EU-G",
    },
    {
        "paragraph": "§4 Nr. 1b UStG",
        "category": "K",
        "description_en": "Intra-community supply of goods",
        "vatex_code": "VATEX-EU-IC",
    },
    {
        "paragraph": "§4 Nr. 8 UStG",
        "category": "E",
        "description_en": "Financial and insurance services",
        "vatex_code": "VATEX-EU-D",
    },
    {
        "paragraph": "§4 Nr. 14 UStG",
        "category": "E",
        "description_en": "Medical and healthcare services",
        "vatex_code": "VATEX-EU-F",
    },
    {
        "paragraph": "§19 UStG",
        "category": "E",
        "description_en": "Kleinunternehmerregelung (small business exemption, turnover < €22,000/year)",
        "vatex_code": "VATEX-EU-O",
        # [NEED: verify 2024 threshold — raised from €17,500 to €22,000]
    },
]


class TaxRulesInput(BaseModel):
    """Input schema for tax_rules."""

    query: str = Field(
        ...,
        description=(
            "What to look up. Examples: 'reverse_charge', 'rates', 'exemptions', "
            "'kleinunternehmer', '13b', 'zero_rate', 'vatex_codes', "
            "or a free-text question about German VAT."
        ),
    )
    context: str | None = Field(
        None,
        description=(
            "Optional context about the transaction, e.g. 'construction services' "
            "or 'intra-community supply'. Used to filter relevant rules."
        ),
    )


class TaxRulesOutput(BaseModel):
    """Output schema for tax_rules."""

    query: str
    results: list[dict[str, Any]]
    notes: list[str] = Field(default_factory=list)
    legal_disclaimer: str = Field(
        default=(
            "This information is provided for technical reference only and does not "
            "constitute legal or tax advice. Always consult a qualified tax adviser "
            "(Steuerberater) for binding guidance. Rules are subject to legislative changes."
        )
    )


TOOL_TAX_RULES = types.Tool(
    name="tax_rules",
    description=(
        "Query German VAT rules for e-invoicing. "
        "Returns structured information about VAT rates (19%, 7%), VAT category codes, "
        "reverse charge rules under §13b UStG, zero-rate and exemption provisions (§4 UStG), "
        "intra-community supply rules, and VATEX exemption reason codes. "
        "For use when building invoice creation logic or validating VAT treatment."
    ),
    inputSchema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "What to look up: 'rates', 'reverse_charge', 'exemptions', 'vatex_codes', etc.",
            },
            "context": {
                "type": "string",
                "description": "Optional transaction context to filter results.",
            },
        },
    },
)


async def handle_tax_rules(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for tax_rules."""
    try:
        params = TaxRulesInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    query_lower = params.query.lower()
    results: list[dict[str, Any]] = []
    notes: list[str] = []

    if any(kw in query_lower for kw in ("rate", "satz", "19", "7", "prozent")):
        results.extend(_GERMAN_VAT_RATES.values())

    if any(kw in query_lower for kw in ("reverse", "13b", "§13b", "steuerschuld", "umkehr")):
        results.extend(_REVERSE_CHARGE_CASES)
        if params.context:
            context_lower = params.context.lower()
            results = [
                r for r in results
                if any(kw in r.get("description_en", "").lower() for kw in context_lower.split())
            ] or results  # Fall back to all if filter yields nothing

    if any(kw in query_lower for kw in ("exempt", "befreit", "§4", "zero", "null", "klein", "19 ustg")):
        results.extend(_EXEMPTIONS)

    if any(kw in query_lower for kw in ("vatex", "reason code", "exemption code")):
        vatex_codes = [
            {"vatex_code": r.get("vatex_code"), "description_en": r.get("description_en"), "paragraph": r.get("paragraph")}
            for r in _EXEMPTIONS + _REVERSE_CHARGE_CASES
            if r.get("vatex_code")
        ]
        results.extend(vatex_codes)

    if not results:
        notes.append(
            "No specific rules matched the query. "
            "Try: 'rates', 'reverse_charge', 'exemptions', 'vatex_codes', or '13b'."
        )
        results = list(_GERMAN_VAT_RATES.values())

    notes.append("Data reflects German VAT law as of 2025-01-01. [NEED: implement rule versioning]")

    output = TaxRulesOutput(query=params.query, results=results, notes=notes)
    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
