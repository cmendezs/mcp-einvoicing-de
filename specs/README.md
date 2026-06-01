# mcp-einvoicing-de — Specification Assets

This directory contains the authoritative schema, Schematron, and XSLT validation assets
for the two German e-invoicing formats supported by this package.

## Directory layout

```
specs/
├── zugferd/                    ZUGFeRD 2.4 / Factur-X 1.08 (FeRD / FNFE-MPE)
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
│   └── zugferd/                Reference XML examples per profile (from FeRD 2.4 release)
│       ├── MINIMUM/
│       ├── BASIC_WL/
│       ├── BASIC/
│       ├── EN16931/
│       ├── EXTENDED/
│       └── XRECHNUNG/
└── documentation/
    ├── zugferd/                Factur-X 1.08 main spec PDF + profile technical appendices
    └── xrechnung/              XRechnung 3.0.2 specification PDF (2024-06-20)
```

## Sources and versions

| Asset | Version | Source |
|---|---|---|
| ZUGFeRD / Factur-X Schematron + XSLT | 1.08 (2025-12-04) | FeRD / FNFE-MPE release package |
| CII D22B base XSD | D22B | UN/CEFACT, bundled in Factur-X 1.08 release |
| XRechnung validator configuration | 3.0.2 / 2026-01-31 | [itplr-kosit/validator-configuration-xrechnung v2026-01-31](https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/tag/v2026-01-31) |
| XRechnung specification PDF | 3.0 / 2024-06-20 | xeinkauf.de |

## Profile URNs

| Profile | URN |
|---|---|
| MINIMUM | `urn:factur-x.eu:1p0:minimum` |
| BASIC WL | `urn:factur-x.eu:1p0:basicwl` |
| BASIC | `urn:factur-x.eu:1p0:basic` |
| EN 16931 (COMFORT) | `urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:en16931` |
| EXTENDED | `urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended` |
| XRechnung 3.0 (CIUS) | `urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0` |

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

## License notes

- ZUGFeRD / Factur-X schemas: copyright FeRD and FNFE-MPE. Free to use for
  implementing and testing compliance with the ZUGFeRD and Factur-X standards.
- KoSIT validator configuration: Apache 2.0 (see `xrechnung/LICENSE`).
- CII D22B XSD: UN/CEFACT. Bundled in the FeRD release package.
