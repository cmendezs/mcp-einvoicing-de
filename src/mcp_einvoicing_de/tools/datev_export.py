"""MCP tool: datev_export — produce DATEV CSV from a ZUGFeRDInvoice.

Generates DATEV-compatible CSV output (EXTF format, schema version 700) for
import into DATEV Belegtransfer or DATEV Rechnungswesen. Maps ZUGFeRDInvoice
line items, tax breakdown, and party identifiers to the DATEV
Buchungsstapel (booking batch) format.

DATEV format reference: developer.datev.de (EXTF 700 specification).
[NEED: confirm current EXTF version number against developer.datev.de]
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

import mcp.types as types
from mcp_einvoicing_core.xml_utils import format_error
from pydantic import BaseModel, Field

from mcp_einvoicing_de.models.zugferd import ZUGFeRDInvoice

logger = logging.getLogger(__name__)

# DATEV EXTF header row field count (Buchungsstapel, version 700)
_EXTF_FORMAT_VERSION = 700
_EXTF_FORMAT_CATEGORY = 21  # Buchungsstapel
_EXTF_FORMAT_NAME = "Buchungsstapel"

# DATEV Kontenrahmen: SKR 03 is the most common German chart of accounts.
# These are default contra accounts; real usage requires configuration.
_DEFAULT_REVENUE_ACCOUNT = "8400"  # Erlöse 19% USt (SKR 03)
_DEFAULT_RECEIVABLE_ACCOUNT = "10000"  # Debitoren-Sammelkonto


class DatevExportInput(BaseModel):
    """Input schema for datev_export."""

    invoice: dict[str, Any] = Field(
        ..., description="ZUGFeRDInvoice data to export."
    )
    revenue_account: str = Field(
        _DEFAULT_REVENUE_ACCOUNT,
        description="DATEV revenue account number (Erlöskonto). Default: 8400 (SKR 03, 19% USt).",
    )
    receivable_account: str = Field(
        _DEFAULT_RECEIVABLE_ACCOUNT,
        description="DATEV receivable account number (Debitorenkonto). Default: 10000.",
    )
    consultant_number: str = Field(
        "0",
        description="DATEV Beraternummer (consultant number).",
    )
    client_number: str = Field(
        "1",
        description="DATEV Mandantennummer (client number).",
    )
    fiscal_year_start: str = Field(
        "",
        description="Fiscal year start date (YYYYMMDD). Defaults to Jan 1 of invoice year.",
    )


class DatevExportOutput(BaseModel):
    """Output schema for datev_export."""

    csv_content: str = Field(..., description="DATEV EXTF CSV content.")
    record_count: int = Field(..., description="Number of booking records.")
    total_amount: str = Field(..., description="Total invoice amount.")
    invoice_number: str


TOOL_DATEV_EXPORT = types.Tool(
    name="datev_export",
    description=(
        "Export a ZUGFeRD invoice to DATEV CSV format (EXTF 700, Buchungsstapel). "
        "Produces a CSV file importable by DATEV Belegtransfer or DATEV Rechnungswesen. "
        "Maps invoice line items to DATEV booking records with configurable accounts."
    ),
    inputSchema={
        "type": "object",
        "required": ["invoice"],
        "properties": {
            "invoice": {"type": "object", "description": "ZUGFeRDInvoice data."},
            "revenue_account": {
                "type": "string",
                "default": _DEFAULT_REVENUE_ACCOUNT,
                "description": "DATEV revenue account (Erlöskonto).",
            },
            "receivable_account": {
                "type": "string",
                "default": _DEFAULT_RECEIVABLE_ACCOUNT,
                "description": "DATEV receivable account (Debitorenkonto).",
            },
            "consultant_number": {"type": "string", "default": "0"},
            "client_number": {"type": "string", "default": "1"},
            "fiscal_year_start": {"type": "string", "default": ""},
        },
    },
)


def _format_datev_date(d: date) -> str:
    """Format a date as DDMM for DATEV Buchungsstapel Belegdatum."""
    return f"{d.day:d}{d.month:02d}"


def _tax_code_from_rate(rate: Decimal) -> str:
    """Map a VAT rate to a DATEV BU-Schlüssel (tax code).

    Common German tax codes in the DATEV Buchungsstapel:
    - 0 = no automatic tax posting
    - 2 = 7% reduced rate
    - 3 = 19% standard rate
    - 8 = tax-exempt (§4 UStG)
    - 9 = reverse charge (§13b UStG)
    """
    if rate == Decimal("19") or rate == Decimal("19.00"):
        return "3"
    if rate == Decimal("7") or rate == Decimal("7.00"):
        return "2"
    if rate == Decimal("0") or rate == Decimal("0.00"):
        return "8"
    return "0"


def _build_extf_header(
    consultant_number: str,
    client_number: str,
    fiscal_year_start: str,
    date_from: date,
    date_to: date,
) -> str:
    """Build the DATEV EXTF header row."""
    fy_start = fiscal_year_start or f"{date_from.year}0101"
    fields = [
        '"EXTF"',                          # 1: Format identifier
        str(_EXTF_FORMAT_VERSION),         # 2: Version
        str(_EXTF_FORMAT_CATEGORY),        # 3: Format category
        f'"{_EXTF_FORMAT_NAME}"',          # 4: Format name
        str(_EXTF_FORMAT_VERSION),         # 5: Format version
        "",                                # 6: Generated on (optional)
        "",                                # 7: Reserved
        "",                                # 8: Reserved
        "",                                # 9: Reserved
        "",                                # 10: Reserved
        f'"{consultant_number}"',          # 11: Beraternummer
        f'"{client_number}"',              # 12: Mandantennummer
        f"{fy_start}",                     # 13: WJ-Beginn
        "4",                               # 14: Sachkontenlänge
        f"{date_from.strftime('%Y%m%d')}",  # 15: Datum von
        f"{date_to.strftime('%Y%m%d')}",    # 16: Datum bis
        "",                                # 17: Bezeichnung
        "",                                # 18: Diktatkürzel
        "0",                               # 19: Buchungstyp (0=Finanzbuchführung)
        "0",                               # 20: Rechnungslegungszweck
        "",                                # 21: Festschreibung
        '"EUR"',                           # 22: WKZ
    ]
    return ";".join(fields)


def _build_booking_record(
    amount: Decimal,
    debit_credit: str,
    account: str,
    contra_account: str,
    tax_code: str,
    invoice_date: date,
    invoice_number: str,
    description: str,
) -> list[str]:
    """Build a single DATEV Buchungsstapel record (one row)."""
    record = [""] * 116
    record[0] = str(abs(amount))           # Umsatz
    record[1] = debit_credit               # Soll/Haben (S/H)
    record[2] = '"EUR"'                    # WKZ Umsatz
    record[3] = ""                         # Kurs
    record[4] = ""                         # Basis-Umsatz
    record[5] = ""                         # WKZ Basis-Umsatz
    record[6] = account                    # Konto
    record[7] = contra_account             # Gegenkonto
    record[8] = tax_code                   # BU-Schlüssel
    record[9] = _format_datev_date(invoice_date)  # Belegdatum
    record[10] = f'"{invoice_number}"'     # Belegfeld 1
    record[11] = ""                        # Belegfeld 2
    record[12] = ""                        # Skonto
    record[13] = f'"{description[:60]}"'   # Buchungstext (max 60 chars)
    return record


async def handle_datev_export(arguments: dict[str, Any]) -> list[types.TextContent]:
    """MCP handler for datev_export."""
    try:
        params = DatevExportInput.model_validate(arguments)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(str(exc))))]

    try:
        invoice = ZUGFeRDInvoice.model_validate(params.invoice)
    except Exception as exc:
        return [types.TextContent(type="text", text=json.dumps(format_error(f"Invalid invoice: {exc}")))]

    records: list[list[str]] = []

    if invoice.line_items:
        for item in invoice.line_items:
            net = item.net_amount or Decimal("0")
            rate = Decimal("19")
            if invoice.tax_lines:
                rate = invoice.tax_lines[0].rate
            tax_code = _tax_code_from_rate(rate)
            desc = item.description or item.name or f"Line {item.line_id}"

            records.append(_build_booking_record(
                amount=net,
                debit_credit="S",
                account=params.receivable_account,
                contra_account=params.revenue_account,
                tax_code=tax_code,
                invoice_date=invoice.invoice_date,
                invoice_number=invoice.invoice_number,
                description=desc,
            ))
    else:
        rate = Decimal("19")
        if invoice.tax_lines:
            rate = invoice.tax_lines[0].rate
        tax_code = _tax_code_from_rate(rate)

        records.append(_build_booking_record(
            amount=invoice.tax_inclusive_amount,
            debit_credit="S",
            account=params.receivable_account,
            contra_account=params.revenue_account,
            tax_code=tax_code,
            invoice_date=invoice.invoice_date,
            invoice_number=invoice.invoice_number,
            description=f"Rechnung {invoice.invoice_number}",
        ))

    buf = StringIO()
    header = _build_extf_header(
        consultant_number=params.consultant_number,
        client_number=params.client_number,
        fiscal_year_start=params.fiscal_year_start,
        date_from=invoice.invoice_date,
        date_to=invoice.invoice_date,
    )
    buf.write(header + "\n")

    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_NONE, escapechar="\\")
    for record in records:
        writer.writerow(record)

    output = DatevExportOutput(
        csv_content=buf.getvalue(),
        record_count=len(records),
        total_amount=str(invoice.tax_inclusive_amount),
        invoice_number=invoice.invoice_number,
    )
    return [types.TextContent(type="text", text=output.model_dump_json(indent=2))]
