"""MCP tool: datev_export — produce DATEV CSV from a ZUGFeRDInvoice.

Generates DATEV-compatible CSV output (EXTF format, schema version 700) for
import into DATEV Belegtransfer or DATEV Rechnungswesen. Maps ZUGFeRDInvoice
line items, tax breakdown, and party identifiers to the DATEV
Buchungsstapel (booking batch) format.

DATEV format reference: developer.datev.de (EXTF 700 specification), primary
source bundled at specs/datev/Format_Buchungsstapel.xml (field 9, BU-Schlüssel,
4 chars max; field 10, Belegdatum, format TTMM).
[NEED: confirm current EXTF version number against developer.datev.de]
"""

from __future__ import annotations

import csv
import logging
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

from pydantic import BaseModel, Field

from mcp_einvoicing_de.models.zugferd import GermanTaxCategory, ZUGFeRDInvoice, ZUGFeRDTax

logger = logging.getLogger(__name__)

# DATEV EXTF header row field count (Buchungsstapel, version 700)
_EXTF_FORMAT_VERSION = 700
_EXTF_FORMAT_CATEGORY = 21  # Buchungsstapel
_EXTF_FORMAT_NAME = "Buchungsstapel"

# DATEV Kontenrahmen: SKR 03 is the most common German chart of accounts.
# These are default contra accounts; real usage requires configuration.
_DEFAULT_REVENUE_ACCOUNT = "8400"  # Erlöse 19% USt (SKR 03)
_DEFAULT_RECEIVABLE_ACCOUNT = "10000"  # Debitoren-Sammelkonto


class DatevExportOutput(BaseModel):
    """Output schema for datev_export."""

    csv_content: str = Field(..., description="DATEV EXTF CSV content.")
    record_count: int = Field(..., description="Number of booking records.")
    total_amount: str = Field(..., description="Total invoice amount.")
    invoice_number: str


def _format_datev_date(d: date) -> str:
    """Format a date as TTMM for DATEV Buchungsstapel Belegdatum (field 10).

    Source: specs/datev/Format_Buchungsstapel.xml field 10
    (<FormatExpression>TTMM</FormatExpression>).
    """
    return f"{d.day:02d}{d.month:02d}"


def _bu_key(category: GermanTaxCategory, rate: Decimal, line_kind: str = "revenue") -> str:
    """Map a VAT category + rate to a DATEV BU-Schlüssel (tax code, field 9).

    Source: specs/datev/Format_Buchungsstapel.xml field 9 (BU-Schlüssel, 4
    chars max). ``line_kind`` is "revenue" for the sales/Ausgangsrechnung
    bookings this tool produces (Debitoren-Sammelkonto debit / Erlöskonto
    credit); "expense" codes are included for API completeness but are not
    reachable from this tool's own call sites today.

    Values marked [Verified locally] were confirmed against the bundled
    DATEV EXTF_Buchungsstapel.csv sample ("Schreibwaren" row: BU 9, 19%
    Vorsteuer). Others are [Unverified] pending confirmation against the
    developer.datev.de Appendix > "Buchungsschlüssel (BU)" page — tracked as
    a v0.8.1 follow-up.
    """
    if category == GermanTaxCategory.REVERSE_CHARGE:
        return "94"  # [Unverified] §13b UStG reverse charge
    if category == GermanTaxCategory.INTRA_COMMUNITY:
        return "91"  # [Unverified] §4 Nr. 1b UStG intra-community supply
    if category in (
        GermanTaxCategory.EXEMPT,
        GermanTaxCategory.SERVICES_OUTSIDE_SCOPE,
        GermanTaxCategory.EXPORT,
        GermanTaxCategory.NOT_SUBJECT,
    ):
        return ""  # no Automatik-BU; book to a manual tax-exempt account
    # category == STANDARD (GermanTaxCategory.REDUCED is an alias of STANDARD;
    # the 7%/19% distinction is carried by `rate`, not by category).
    if line_kind == "revenue":
        return ""  # [Unverified] revenue Automatikkonto already encodes the rate (SKR03/04)
    if rate == Decimal("19") or rate == Decimal("19.00"):
        return "9"  # [Verified locally] Vorsteuer 19% — EXTF_Buchungsstapel.csv "Schreibwaren" row
    if rate == Decimal("7") or rate == Decimal("7.00"):
        return "8"  # [Unverified] Vorsteuer 7%
    return ""


def _resolve_line_tax(item: Any, tax_lines: list[ZUGFeRDTax]) -> tuple[GermanTaxCategory, Decimal]:
    """Resolve the (category, rate) pair for one invoice line.

    Matches the line's own `tax_category` + `tax_rate` against the invoice's
    VAT breakdown (`tax_lines`) so mixed-rate and reverse-charge invoices are
    keyed correctly instead of applying `tax_lines[0]` to every line
    (DE-TL-1). Falls back to `tax_lines[0]` — and logs a warning that the
    export is degraded — only when no matching breakdown entry is found.
    """
    item_category = getattr(item, "tax_category", None)
    item_rate = getattr(item, "tax_rate", None)
    if item_category is not None and item_rate is not None:
        for tax_line in tax_lines:
            if tax_line.category == item_category and tax_line.rate == item_rate:
                return GermanTaxCategory(item_category), item_rate

    logger.warning(
        "Line %s: no matching tax_lines entry for category=%s rate=%s; "
        "falling back to tax_lines[0] (degraded export)",
        getattr(item, "line_id", "?"),
        item_category,
        item_rate,
    )
    if tax_lines:
        return tax_lines[0].category, tax_lines[0].rate
    return GermanTaxCategory.STANDARD, Decimal("19")


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
        '"EXTF"',  # 1: Format identifier
        str(_EXTF_FORMAT_VERSION),  # 2: Version
        str(_EXTF_FORMAT_CATEGORY),  # 3: Format category
        f'"{_EXTF_FORMAT_NAME}"',  # 4: Format name
        str(_EXTF_FORMAT_VERSION),  # 5: Format version
        "",  # 6: Generated on (optional)
        "",  # 7: Reserved
        "",  # 8: Reserved
        "",  # 9: Reserved
        "",  # 10: Reserved
        f'"{consultant_number}"',  # 11: Beraternummer
        f'"{client_number}"',  # 12: Mandantennummer
        f"{fy_start}",  # 13: WJ-Beginn
        "4",  # 14: Sachkontenlänge
        f"{date_from.strftime('%Y%m%d')}",  # 15: Datum von
        f"{date_to.strftime('%Y%m%d')}",  # 16: Datum bis
        "",  # 17: Bezeichnung
        "",  # 18: Diktatkürzel
        "0",  # 19: Buchungstyp (0=Finanzbuchführung)
        "0",  # 20: Rechnungslegungszweck
        "",  # 21: Festschreibung
        '"EUR"',  # 22: WKZ
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
    record[0] = str(abs(amount))  # Umsatz
    record[1] = debit_credit  # Soll/Haben (S/H)
    record[2] = '"EUR"'  # WKZ Umsatz
    record[3] = ""  # Kurs
    record[4] = ""  # Basis-Umsatz
    record[5] = ""  # WKZ Basis-Umsatz
    record[6] = account  # Konto
    record[7] = contra_account  # Gegenkonto
    record[8] = tax_code  # BU-Schlüssel
    record[9] = _format_datev_date(invoice_date)  # Belegdatum
    record[10] = f'"{invoice_number}"'  # Belegfeld 1
    record[11] = ""  # Belegfeld 2
    record[12] = ""  # Skonto
    record[13] = f'"{description[:60]}"'  # Buchungstext (max 60 chars)
    return record


async def datev_export(
    invoice: dict[str, Any],
    revenue_account: str = _DEFAULT_REVENUE_ACCOUNT,
    receivable_account: str = _DEFAULT_RECEIVABLE_ACCOUNT,
    consultant_number: str = "0",
    client_number: str = "1",
    fiscal_year_start: str = "",
) -> dict[str, Any]:
    """Export a ZUGFeRD invoice to DATEV CSV format (EXTF 700, Buchungsstapel).

    Produces a CSV file importable by DATEV Belegtransfer or DATEV
    Rechnungswesen. Maps invoice line items to DATEV booking records with
    configurable accounts.

    Args:
        invoice: ZUGFeRDInvoice data to export.
        revenue_account: DATEV revenue account number (Erloskonto).
            Default: 8400 (SKR 03, 19% USt).
        receivable_account: DATEV receivable account number
            (Debitorenkonto). Default: 10000.
        consultant_number: DATEV Beraternummer (consultant number).
        client_number: DATEV Mandantennummer (client number).
        fiscal_year_start: Fiscal year start date (YYYYMMDD). Defaults to
            Jan 1 of invoice year.
    """
    try:
        invoice_model = ZUGFeRDInvoice.model_validate(invoice)
    except Exception as exc:
        return {"error": f"Invalid invoice: {exc}"}

    records: list[list[str]] = []

    if invoice_model.line_items:
        for item in invoice_model.line_items:
            category, rate = _resolve_line_tax(item, invoice_model.tax_lines)
            tax_code = _bu_key(category, rate, line_kind="revenue")
            desc = item.description or item.name or f"Line {item.line_id}"

            # Post gross (net + line VAT) in both branches (DE-TL-3): the
            # no-lines branch below always posts invoice.tax_inclusive_amount
            # (gross); the per-line branch previously posted net only,
            # producing inconsistent totals for mixed-rate invoices.
            # [Verified locally] against the bundled DATEV EXTF sample
            # ("Aufteilung AR ohne Automatikkonto": 1190,00 = 1000,00 net +
            # 190,00 VAT at 19% brutto).
            line_tax = (item.line_net_amount * rate / Decimal("100")).quantize(Decimal("0.01"))
            gross = item.line_net_amount + line_tax

            records.append(
                _build_booking_record(
                    amount=gross,
                    debit_credit="S",
                    account=receivable_account,
                    contra_account=revenue_account,
                    tax_code=tax_code,
                    invoice_date=invoice_model.invoice_date,
                    invoice_number=invoice_model.invoice_number,
                    description=desc,
                )
            )
    else:
        category = GermanTaxCategory.STANDARD
        rate = Decimal("19")
        if invoice_model.tax_lines:
            category = invoice_model.tax_lines[0].category
            rate = invoice_model.tax_lines[0].rate
        tax_code = _bu_key(category, rate, line_kind="revenue")

        records.append(
            _build_booking_record(
                amount=invoice_model.tax_inclusive_amount,
                debit_credit="S",
                account=receivable_account,
                contra_account=revenue_account,
                tax_code=tax_code,
                invoice_date=invoice_model.invoice_date,
                invoice_number=invoice_model.invoice_number,
                description=f"Rechnung {invoice_model.invoice_number}",
            )
        )

    buf = StringIO()
    header = _build_extf_header(
        consultant_number=consultant_number,
        client_number=client_number,
        fiscal_year_start=fiscal_year_start,
        date_from=invoice_model.invoice_date,
        date_to=invoice_model.invoice_date,
    )
    buf.write(header + "\n")

    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_NONE, escapechar="\\")
    for record in records:
        writer.writerow(record)

    output = DatevExportOutput(
        csv_content=buf.getvalue(),
        record_count=len(records),
        total_amount=str(invoice_model.tax_inclusive_amount),
        invoice_number=invoice_model.invoice_number,
    )
    return output.model_dump()
