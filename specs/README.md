# mcp-einvoicing-de — Specification Assets

This directory contains the authoritative schema, Schematron, and XSLT validation assets
for the two German e-invoicing formats supported by this package.

## Directory layout

```
specs/
├── zugferd/                    ZUGFeRD 2.5.2 / Factur-X 1.09.2 (FeRD / FNFE-MPE)
│   ├── MINIMUM/                Profile MINIMUM — Schematron (.sch), XSD, XSLT/
│   ├── BASICWL/                Profile BASIC WL
│   ├── BASIC/                  Profile BASIC
│   ├── EN16931/                Profile EN 16931 (COMFORT)
│   ├── EXTENDED/               Profile EXTENDED
│   └── XSD_CII_D22B/           UN/CEFACT CII D22B base XSD
├── xrechnung/                  XRechnung 3.0.2 — KoSIT validator configuration 2026-01-31
│   ├── EN16931-CII-validation.xsl   EN 16931 CII XSLT (compiled Schematron)
│   ├── EN16931-UBL-validation.xsl   EN 16931 UBL XSLT
│   ├── scenarios.xml                KoSIT validator scenario configuration
│   └── resources/
│       ├── cii/16b/xsl/        CII EN 16931 validation XSLT
│       ├── ubl/2.1/xsl/        UBL EN 16931 validation XSLT
│       ├── xrechnung/3.0.2/xsl/  XRechnung CIUS CII and UBL validation XSLT
│       └── xsd/                KoSIT report and scenarios XSD
├── examples/
│   └── zugferd/                Reference XML examples per profile (from FeRD 2.5.2 release)
│       ├── MINIMUM/
│       ├── BASIC_WL/
│       ├── BASIC/
│       ├── EN16931/
│       ├── EXTENDED/
│       └── XRECHNUNG/          Not refreshed by the 2.5.2 update (ZUGFeRD-only package; see below)
└── documentation/
    ├── zugferd/                Factur-X 1.09.2 main spec PDF + profile technical appendices + EN 16931 codelist xlsx
    └── xrechnung/              XRechnung 3.0.2 specification PDF (2024-06-20)
```

## Sources and versions

| Asset | Version | Source |
|---|---|---|
| ZUGFeRD / Factur-X Schema + Schematron + XSLT + Examples + Documentation | 2.5.2 / 1.09.2 (2026-08-04, effective 2026-09-01) | FeRD / FNFE-MPE release package `ZUGFeRD_2.5.2_EN.zip`, retrieved 2026-08-09 |
| CII D22B base XSD | D22B | UN/CEFACT; byte-identical to the previously bundled 1.08 copy — confirmed via diff, not re-copied |
| XRechnung validator configuration | 3.0.2 / 2026-01-31 | [itplr-kosit/validator-configuration-xrechnung v2026-01-31](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/tag/v2026-01-31) — untouched by this update, XRechnung ships separately from the FeRD ZUGFeRD/Factur-X package |
| XRechnung specification PDF | 3.0 / 2024-06-20 | xeinkauf.de |

**2026-08-09 update notes:**
- Upgraded from the previously bundled ZUGFeRD 2.4 / Factur-X 1.08 (2025-12-04). `specs/examples/zugferd/{MINIMUM,BASIC_WL,BASIC,EN16931,EXTENDED}/` were flattened from the release package's per-example subfolders to match this package's existing flat-per-profile convention (filenames retained as shipped by FeRD, e.g. `B01_01_Einfach.xml`).
- General change: in BASIC WL, BASIC, and EN16931, rule `BR-CO-27` was renamed to `CII-SR-470` (no functional change).
- EXTENDED profile: BT-151/BT-151-0 cardinality relaxed `1..1` → `0..1` (`BR-FXEXT-CO-04` keeps it mandatory for DETAIL/no-subtype lines); `BR-S-1`/`BR-Z-1`/`BR-E-1`/`BR-AE-1`/`BR-IC-1`/`BR-G-1`/`BR-O-1`/`BR-AF-1`/`BR-AG-1` replaced by the `BR-FXEXT-*-01` series (allows >1 VAT Breakdown per category/exemption); `BR-54` split into `BR-FXEXT-BR-54-1`/`-2`; `BR-FXEXT-08` rounding fix for BT-131 sums. The BT-151 cardinality relaxation only matters for lines using `SubInvoiceLine`/subtype (BT-X-8) `GROUP`/`INFORMATION`, which `ZUGFeRDLineItem` does not currently model — no code change was needed for that specific item.
- Verified via the full local test suite (`pytest`, 133 passed) including Saxon-executed validation of the new stylesheets against the bundled 2.5.2 example set, plus an ad hoc comparison showing the new EXTENDED stylesheet produces the *same or fewer* findings than the old one against a hand-built sample invoice (one pre-existing, unrelated finding — missing `currencyID` on `TaxTotalAmount` per `BR-FXEXT-CO-15` — reproduces identically under both the old and new stylesheet, so it predates this update; tracked separately as DE-ZF252-3 in `roadmap-2026.md`).

## Profile URNs

| Profile | URN |
|---|---|
| MINIMUM | `urn:factur-x.eu:1p0:minimum` |
| BASIC WL | `urn:factur-x.eu:1p0:basicwl` |
| BASIC | `urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic` |
| EN 16931 (COMFORT) | `urn:cen.eu:en16931:2017` |
| EXTENDED | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended` |
| XRechnung 3.0 (CIUS) | `urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0` |

**Corrected 2026-08-09:** BASIC was missing the `urn:cen.eu:en16931:2017#compliant#` prefix
and EN 16931 carried a spurious `#compliant#urn:factur-x.eu:1p0:en16931` suffix that does
not appear in any official ZUGFeRD 2.5.2 example. Verified directly against the
`ram:GuidelineSpecifiedDocumentContextParameter/ram:ID` value in 32 bundled example
instances covering all five profiles. This matches the fix already applied to
`ZUGFeRDProfile` in `models/zugferd.py` (v0.8.2).

## Schematron stylesheet keys (used by invoice_validate tool)

The `_PROFILE_TO_STYLESHEET` map in
`mcp_einvoicing_de/tools/invoice_validate.py` references these keys:

| Key | File |
|---|---|
| `zugferd_minimum_cii` | `zugferd/MINIMUM/XSLT/FACTUR-X_MINIMUM.xslt` |
| `zugferd_basicwl_cii` | `zugferd/BASICWL/XSLT/FACTUR-X_BASIC-WL.xslt` |
| `zugferd_basic_cii` | `zugferd/BASIC/XSLT/FACTUR-X_BASIC.xslt` |
| `en16931_cii` | `zugferd/EN16931/XSLT/FACTUR-X_EN16931.xslt` |
| `en16931_ubl` | `xrechnung/resources/ubl/2.1/xsl/EN16931-UBL-validation.xsl` |
| `zugferd_extended_cii` | `zugferd/EXTENDED/XSLT/FACTUR-X_EXTENDED.xslt` |
| `xrechnung_cii` | `xrechnung/resources/xrechnung/3.0.2/xsl/XRechnung-CII-validation.xsl` |
| `xrechnung_ubl` | `xrechnung/resources/xrechnung/3.0.2/xsl/XRechnung-UBL-validation.xsl` |

## DATEV (`specs/datev/`)

Reference material for the `datev_export` tool's DATEV EXTF Buchungsstapel mapping.

- **Source portal**: https://developer.datev.de/
- **Format name / version**: EXTF Buchungsstapel, format version 13
- **Retrieval date**: 2026-07-18
- **Files bundled**:
  - `EXTF_Buchungsstapel.csv` — sample export data (from `Musterdaten_DATEV_Format`),
    dated 2025-06-18, format `EXTF`, doc-type `700`, name `Buchungsstapel`, version `13`
  - `Format_Buchungsstapel.xml` — field-level format specification (`<Version>13</Version>`),
    the primary source cited in `tools/datev_export.py`
  - `Formate/*.xml` — the DATEV Format-Prüfprogramm's bundled format rulesets (text, 287 files)
- **Deliberately not committed**: `DatevFormatPruefProgramm.exe`, the compiled Format-Prüfprogramm
  v2.2.3.0 CLI validator. Unlike the CSV/XML text specs, distributing a proprietary DATEV
  binary through a public git repository is a distinct redistribution question from excluding
  it out of the PyPI wheel, and DATEV's actual terms of use for `developer.datev.de` downloads
  were never verified `[Unverified]`. It is git-ignored (see `.gitignore`); re-download it from
  `developer.datev.de` locally if you need it for the CI follow-up below.
- **Also deliberately not committed**: DATEV Serviceinformation PDFs such as Dok.-Nr. 1008613
  ("Übersicht Steuerschlüssel (BU) in DATEV Unternehmen online"), used locally to verify the
  `_bu_key` BU-Schlüssel mappings in `tools/datev_export.py` (DE-TL-1). These are copyrighted
  DATEV publications, git-ignored (`specs/datev/*.pdf`); re-download from DATEV if needed.

Consumer: [`tools/datev_export.py`](../src/mcp_einvoicing_de/tools/datev_export.py)
cites `Format_Buchungsstapel.xml` field 9 (BU-Schlüssel) and field 10 (Belegdatum,
`TTMM`) in its module docstring.

**Follow-up**: wiring the DATEV Format-Prüfprogramm into CI (via Wine on Linux runners
against a locally-supplied `.exe`, or by parsing the bundled `Formate/*.xml` rulesets
directly instead) as a sanity check on `datev_export` output is tracked as a v0.8.1/v0.9.0
follow-up; confirming DATEV's redistribution terms should happen first if the CLI binary
approach is chosen.

## License notes

- ZUGFeRD / Factur-X schemas: copyright FeRD and FNFE-MPE. Free to use for
  implementing and testing compliance with the ZUGFeRD and Factur-X standards.
- KoSIT validator configuration: Apache 2.0 (see `xrechnung/LICENSE`).
- CII D22B XSD: UN/CEFACT. Bundled in the FeRD release package.
- DATEV EXTF Buchungsstapel format spec: copyright DATEV eG, distributed via
  `developer.datev.de`. The CSV/XML text specs are bundled here for internal
  reference only; not redistributed as part of the published PyPI wheel
  (`specs/` lives outside `src/mcp_einvoicing_de/` and is excluded from the
  package build). The compiled `DatevFormatPruefProgramm.exe` CLI validator is
  additionally excluded from git entirely (not just the wheel) — see the DATEV
  section above.
