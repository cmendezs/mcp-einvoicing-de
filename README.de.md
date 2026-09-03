# mcp-einvoicing-de 🇩🇪

[English](README.md) | [Deutsch](README.de.md)

<!-- mcp-name: io.github.cmendezs/mcp-einvoicing-de -->

![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
[![PyPI version](https://img.shields.io/pypi/v/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![mcp-einvoicing-de MCP server](https://glama.ai/mcp/servers/cmendezs/mcp-einvoicing-de/badges/score.svg)](https://glama.ai/mcp/servers/cmendezs/mcp-einvoicing-de)

MCP-Server (Model Context Protocol) in Python für die **deutsche elektronische Rechnung** in den Formaten **ZUGFeRD 2.x** und **XRechnung 3.x** (EN 16931, FeRD, KoSIT). Ermöglicht KI-Agenten (Claude, IDEs) das Erstellen, Validieren, Parsen und Konvertieren von E-Rechnungen, die vollständig dem deutschen B2B-E-Rechnungsmandat (gültig ab 2025, schrittweise Durchsetzung bis 2027 bis 2028) und der europäischen Norm EN 16931 entsprechen.

---

## Einführung

Dieses Paket basiert auf [**mcp-einvoicing-core**](https://github.com/cmendezs/mcp-einvoicing-core), einer gemeinsamen Basisbibliothek für europäische E-Rechnungs-MCP-Server. Sie stellt gemeinsame Modelle, Validierungsabstraktionen, XML-Hilfsfunktionen und die Ausnahmehierarchie bereit.

`mcp-einvoicing-core` wird automatisch als transitive Abhängigkeit installiert, kein zusätzlicher Schritt erforderlich.

> **Für Entwickler:** `pip install -e ".[dev]"` installiert das Basispaket automatisch aus PyPI.

## Installation

### Über PyPI (empfohlen)

```bash
pip install mcp-einvoicing-de
```

Ohne vorherige Installation mit `uvx`:

```bash
uvx mcp-einvoicing-de
```

### Aus den Quellen

```bash
git clone https://github.com/cmendezs/mcp-einvoicing-de.git
cd mcp-einvoicing-de

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

### Optionale Extras

| Extra | Zweck | Installation |
|-------|-------|--------------|
| `[xslt2]` | Saxon-HE-Backend für XSLT-2.0-Schematron-Stylesheets (FeRD Factur-X 1.09.2 und KoSIT XRechnung 3.0.2). Erforderlich für lokale Schematron-Validierung; lxml unterstützt nur XSLT 1.0. | `pip install mcp-einvoicing-de[xslt2]` |
| `[pdf]` | Zusaetzliche PDF-Hilfsfunktionen fuer die Extraktion eingebetteter XML-Dateien (`pikepdf` ist auch eine Basisabhaengigkeit fuer die PDF/A-3-Generierung). | `pip install mcp-einvoicing-de[pdf]` |
| `[pymupdf]` | Alternative PDF-Engine (verwendet `PyMuPDF`). | `pip install mcp-einvoicing-de[pymupdf]` |
| `[dev]` | Entwicklungswerkzeuge (pytest, ruff, pre-commit). | `pip install mcp-einvoicing-de[dev]` |

## Konfiguration

Der Server benötigt keine externen Zugangsdaten. Verfügbare Umgebungsvariablen:

| Variable | Beschreibung | Standard |
|----------|-------------|---------|
| `EINVOICING_DE_LOG_LEVEL` | Protokollierungsgrad (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `EINVOICING_DE_KOSIT_VALIDATOR_URL` | URL eines selbst gehosteten KoSIT-Validierungstool-REST-Endpunkts. Wird nur verwendet, wenn die Cloud-Validierung aktiviert ist — siehe `EINVOICING_DE_KOSIT_ENABLE` | |
| `EINVOICING_DE_KOSIT_ENABLE` | Auf `1` setzen, um die KoSIT-Cloud-Validierung zu aktivieren (`validator.kosit.de` oder ein selbst gehosteter Endpunkt). Standardmaessig laeuft nur lokales Schematron | |
| `EINVOICING_PEPPOL_CODELIST_DIR` | Lokales Verzeichnis mit einer eigenen Kopie der OpenPeppol eDEC Code Lists, erforderlich fuer die Peppol-Codelist-Werkzeuge (nicht in diesem Paket enthalten; siehe README von `mcp-einvoicing-core`) | |
| `EINVOICING_EN16931_CODELIST_DIR` | Lokales Verzeichnis mit einer eigenen Kopie der EN-16931-Codelisten des CEF "Digital Building Blocks", erforderlich fuer die EN-16931-Codelist-Werkzeuge (nicht enthalten; siehe README von `mcp-einvoicing-core`) | |

Die EUSR/TSR-Reporting- und MLS-Werkzeuge erfordern zusaetzlich das `[xslt2]`-Extra fuer die Schematron-Validierung.

## Integration Claude Desktop

Eintrag in die Datei `claude_desktop_config.json`. Es sind keine Umgebungsvariablen erforderlich:

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "uvx",
      "args": ["mcp-einvoicing-de"]
    }
  }
}
```

## Integration Cursor

Cursor unterstuetzt MCP-Server ueber stdio. Konfiguration hinzufuegen in:
- **Global** (alle Projekte): `~/.cursor/mcp.json`
- **Projekt** (nur dieses Repository): `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "uvx",
      "args": ["mcp-einvoicing-de"]
    }
  }
}
```

Laden Sie das Cursor-Fenster neu (`Ctrl+Shift+P` dann *Reload Window*), um die Aenderungen zu uebernehmen.

## Integration Kiro

Kiro unterstuetzt MCP-Server ueber eine dedizierte Konfigurationsdatei. Zwei Ebenen sind verfuegbar:
- **Global** (alle Projekte): `~/.kiro/settings/mcp.json`
- **Workspace** (nur dieses Repository): `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "einvoicing-de": {
      "command": "uvx",
      "args": ["mcp-einvoicing-de"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Die Datei wird beim Speichern automatisch neu geladen. Sie koennen die Konfiguration auch ueber die Befehlspalette (`Cmd+Shift+P` / `Ctrl+Shift+P`) und dann *MCP* oeffnen.

## Verfügbare Werkzeuge

| Werkzeug | Beschreibung |
|----------|-------------|
| `invoice_create` | ZUGFeRD- oder XRechnung-XML (CII oder UBL) erzeugen. Erzwingt das B2B-Mandat nach §14 Abs. 2 UStG: Nicht-XML-Ausgaben werden fuer deutsche Rechnungsempfaenger mit USt-IdNr. (DE-Praefix) abgelehnt, sofern nicht `transitional_period_opt_in=True` gesetzt ist. `output_format='pdf'` erzeugt eine PDF/A-3-Hybridrechnung der Stufe B mit sRGB-ICC-Profil, OutputIntent, eingebetteten Schriften und deterministischer /ID. |
| `invoice_validate` | Rechnung gegen EN 16931 und KoSIT-Regeln (BR-DE-\*) pruefen. Standardmaessig laeuft nur lokale Schematron-Validierung (es verlassen keine Daten den eigenen Rechner); mit `cloud_validate=True` oder `EINVOICING_DE_KOSIT_ENABLE=1` die KoSIT-Cloud-Validierung (`validator.kosit.de` oder ein selbst gehosteter Endpunkt) mit exponentiellem Backoff-Retry (1s/2s/4s) aktivieren. Lokale XSLT-2.0-Validierung erfordert das Extra `[xslt2]`. |
| `invoice_parse` | Strukturierte Daten aus ZUGFeRD- oder XRechnung-XML extrahieren oder aus einer PDF/A-3-Hybridrechnung mit eingebetteter `factur-x.xml` / `zugferd-invoice.xml`. |
| `invoice_convert` | Zwischen ZUGFeRD-Profilen konvertieren, ZUGFeRD/XRechnung-CII-Header tauschen oder Cross-Syntax-Konvertierung CII/UBL ueber Core `convert_wire_format` durchfuehren. |
| `datev_export` | ZUGFeRD-Rechnung als DATEV-EXTF-700-Buchungsstapel-CSV-Datei fuer den Import in DATEV-Buchhaltungssoftware exportieren. Standardmaessig SKR-03-Konten (8400 Erloese / 10000 Forderungen). |
| `tax_rules` | Deutsche Umsatzsteuerregeln abfragen (Saetze, §13b-UStG-Reverse-Charge-Codes, §19-UStG-Kleinunternehmerschwellen nach JStG 2024 mit 25.000 EUR Vorjahr / 100.000 EUR laufendes Jahr, Befreiungen). |

### Peppol-Netzwerkwerkzeuge

Peppol-Teilnehmersuche, Suche nach Service-Endpunkten, eine reine DNS-Diagnose, AS4-Versand, Peppol-Directory-Suche und die Codelist-Werkzeuge von OpenPeppol eDEC werden vom gemeinsamen Peppol-Werkzeug-Plugin des Core (`mcp_einvoicing_core.peppol.tools.register_peppol_tools`) bereitgestellt, das in `server.py` mit einem deutschlandspezifischen Identifikator-Adapter eingebunden ist: eine blanke USt-IdNr. (z. B. `123456789` oder `DE123456789`) wird auf das Peppol-Schema `9930:<Wert>` (`DE:VAT`) normalisiert; ein bereits schema-qualifizierter Identifikator (z. B. `9930:DE123456789` oder `0204:<Leitweg-ID>` fuer per Leitweg-ID geroutete B2G-Rechnungen) bleibt unveraendert. Fuer den Versand per AS4 zunaechst XRechnung UBL mit `invoice_convert` (oder `invoice_create` mit `target_syntax='UBL'`) erzeugen und das Ergebnis dann an `peppol_send` uebergeben.

`peppol_send` signiert ausgehende Nachrichten seit `mcp-einvoicing-core` v1.20.0 mit einer echten `wsse:Security`-Signatur (zuvor berechnet und verworfen — siehe CHANGELOG.md v0.10.0).

| Werkzeug | Beschreibung |
|---|---|
| `peppol_lookup_participant` | Prueft, ob ein Unternehmen im Peppol-Netzwerk registriert ist; liefert Registrierungsstatus und unterstuetzte Dokumenttypen |
| `peppol_get_service_endpoint` | Ruft den AS4-Endpunkt fuer den Dokumenttyp eines Teilnehmers ab |
| `resolve_peppol_dns` | Reine DNS-Diagnose (SML), unabhaengig von der SMP-Erreichbarkeit |
| `peppol_send` | Uebertraegt eine UBL/CII-Rechnung per AS4 |
| `peppol_directory_search` | Durchsucht das oeffentliche Peppol Directory nach Teilnehmer, Name, Land oder Dokumenttyp |
| `list_participant_id_schemes`, `list_document_type_ids`, `list_process_ids`, `list_spis_use_case_ids` | OpenPeppol-eDEC-Codelist-Abfragen (erfordern `EINVOICING_PEPPOL_CODELIST_DIR`) |
| `check_document_type_id_in_codelist`, `check_process_id_in_codelist`, `check_participant_id_scheme_in_codelist`, `get_peppol_codelist_version` | OpenPeppol-eDEC-Codelist-Pruefungen und Versionsabfrage |

Vollstaendige Parameterdokumentation zu diesen Werkzeugen siehe [README von `mcp-einvoicing-core`](https://github.com/cmendezs/mcp-einvoicing-core#readme).

### Peppol-Reporting- und Statuswerkzeuge

Hinzugefuegt in v0.10.0 ueber drei optionale Core-Plugins, die bedingungslos in `server.py` eingebunden werden. Jedes liefert einen klaren Fehler beim Aufruf (nicht bei der Registrierung), wenn das zugehoerige Extra oder Datenverzeichnis fehlt.

| Werkzeug | Plugin | Beschreibung |
|---|---|---|
| `validate_eusr_report` | `register_peppol_reporting_tools` | Validiert einen End User Statistics Report (XSD, dann Schematron). Erfordert das `[xslt2]`-Extra. |
| `validate_tsr_report` | `register_peppol_reporting_tools` | Validiert einen Transaction Statistics Report (XSD, dann Schematron). Erfordert das `[xslt2]`-Extra. |
| `validate_mls_message` | `register_peppol_mls_tools` | Validiert ein Message-Level-Status-Dokument (UBL-`ApplicationResponse-2`-Teilmenge). Erfordert das `[xslt2]`-Extra. |
| `build_mls_message` | `register_peppol_mls_tools` | Erstellt eine MLS-Antwort auf Dokumentebene. Erfordert das `[xslt2]`-Extra. |
| 13 `list_*`/`check_*`-Paare, `get_en16931_codelist_version` | `register_en16931_codelist_tools` | Abfragen/Pruefungen der semantischen EN-16931-Codelisten (Einheiten, USt-Kategorien usw.). Erfordern `EINVOICING_EN16931_CODELIST_DIR`. |

Vollstaendige Parameterdokumentation zu diesen Werkzeugen siehe [README von `mcp-einvoicing-core`](https://github.com/cmendezs/mcp-einvoicing-core#readme).

### Verwendungsbeispiele

**Beispiel 1: Rechnung validieren**

```
1. invoice_validate(
     xml_base64="...",   # Base64-kodiertes ZUGFeRD-XML
     strict=True
   )
   → {
       "is_valid": true,
       "profile": "EN_16931",
       "syntax": "CII",
       "error_count": 0,
       "warning_count": 2,
       "errors": [],
       "warnings": [...],
       "validator_used": "local_schematron"
     }
```

**Beispiel 2: Deutsche Steuerregeln abfragen**

```
2. tax_rules(query="reverse_charge", context="Bauleistungen")
   → {
       "results": [
         {
           "paragraph": "§13b Abs. 2 Nr. 5 UStG",
           "description_en": "Construction services (building contractor rule)",
           "vatex_code": "VATEX-EU-AE",
           "invoice_note": "Steuerschuldnerschaft des Leistungsempfängers (§13b UStG)"
         }
       ],
       "legal_disclaimer": "..."
     }
```

**Beispiel 3: Peppol-Registrierung prüfen**

```
3. peppol_lookup_participant(
     identifier="123456789",   # blanke USt-IdNr., normalisiert zu 9930:DE123456789
     environment="production"
   )
   → {
       "is_registered": true,
       "participant_id": "9930:DE123456789",
       "supported_document_types": ["urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"],
       "smp_hostname": "b-...iso6523-actorid-upis.edelivery.tech.ec.europa.eu"
     }
```

**Beispiel 4: Rechnungsdaten parsen**

```
4. invoice_parse(xml_base64="...", include_raw_xml=False)
   → {
       "profile": "XRECHNUNG",
       "syntax": "CII",
       "invoice_number": "RE-2025-001",
       "invoice_date": "2025-01-15",
       "seller_name": "Muster GmbH",
       "buyer_name": "Käufer AG",
       "tax_inclusive_amount": "119.00",
       "currency_code": "EUR"
     }
```

## Architektur

```
mcp-einvoicing-de (dieses Paket, eigenständiger MCP-Server)
├── ZUGFeRDInvoice / XRechnungInvoice  ← Pydantic-Modelle (alle Profile)
├── SchematronValidator                ← EN 16931 + KoSIT BR-DE-* Regeln
├── KoSITValidator                     ← Remote-Validierungstool (optional)
└── Tools: create / validate / parse / convert / datev_export / tax_rules
    (+ Peppol-Werkzeug-Plugin des Core, separat eingebunden: lookup / send / DNS / codelists)

        ↑ erweitert
mcp-einvoicing-core (gemeinsame Basis, als Abhängigkeit installiert)
├── BaseDocumentGenerator / Validator / Parser
├── BaseInvoice, BaseParty … (Pydantic)
├── xml_utils, exceptions
└── EInvoicingMCPServer
```

## Unterstützte Standards

| Standard | Version | Profile / Syntax |
|----------|---------|-----------------|
| ZUGFeRD | 2.5.2 | MINIMUM, BASIC WL, BASIC, EN 16931, EXTENDED |
| XRechnung | 3.0.2 | CII (Cross Industry Invoice), UBL (Universal Business Language) |
| EN 16931 | 2017 | Europäisches Kerndatenmodell für die elektronische Rechnung |
| Peppol BIS | 3.0 | Billing 3.0 (EN-16931-konform) |

> **Hinweis:** ZUGFeRD 2.x und XRechnung 3.x teilen auf Profilebene EN 16931 dieselbe CII-XML-Syntax. Eine Konvertierung zwischen beiden Formaten ist daher ohne Datenverlust möglich. Das EXTENDED-Profil ist ZUGFeRD-spezifisch und hat kein XRechnung-Äquivalent.

| Ressource | Link |
|-----------|------|
| FeRD ZUGFeRD-Spezifikation | [ferd-net.de](https://www.ferd-net.de) |
| KoSIT XRechnung | [xeinkauf.de](https://xeinkauf.de/xrechnung/) |
| KoSIT Validierungstool | [github.com/itplr-kosit/validationtool](https://github.com/itplr-kosit/validationtool) |
| EN 16931-1:2017 | [CEN](https://www.cen.eu/) |
| Peppol BIS Billing 3.0 | [docs.peppol.eu](https://docs.peppol.eu/poacc/billing/3.0/) |

## Tests

```bash
# Entwicklungsabhängigkeiten installieren
pip install -e ".[dev]"

# Gesamte Testsuite ausführen
pytest tests/ -v

# Mit Abdeckungsbericht
pytest --cov=mcp_einvoicing_de --cov-report=term-missing

# Nur Modell-Tests
pytest tests/test_models.py -v
```

## Mitwirken

Beiträge sind willkommen. Bitte öffnen Sie ein Issue, bevor Sie einen Pull Request für wesentliche Änderungen einreichen.

```bash
git clone https://github.com/cmendezs/mcp-einvoicing-de.git
cd mcp-einvoicing-de
pip install -e ".[dev]"
pytest
make audit
```

## Weitere MCP-Server für E-Rechnungen

| Land | Server |
|------|--------|
| 🌍 Global | [mcp-einvoicing-core](https://github.com/cmendezs/mcp-einvoicing-core) |
| 🇧🇪 Belgien | [mcp-einvoicing-be](https://github.com/cmendezs/mcp-einvoicing-be) |
| 🇧🇷 Brasilien | [mcp-nfe-br](https://github.com/cmendezs/mcp-nfe-br) |
| 🇫🇷 Frankreich | [mcp-facture-electronique-fr](https://github.com/cmendezs/mcp-facture-electronique-fr) |
| 🇩🇪 Deutschland | [mcp-einvoicing-de](https://github.com/cmendezs/mcp-einvoicing-de) |
| 🇮🇹 Italien | [mcp-fattura-elettronica-it](https://github.com/cmendezs/mcp-fattura-elettronica-it) |
| 🇲🇽 Mexiko | [mcp-cfdi-mx](https://github.com/cmendezs/mcp-cfdi-mx) |
| 🇵🇱 Polen | [mcp-ksef-pl](https://github.com/cmendezs/mcp-ksef-pl) |
| 🇸🇬 Singapur | [mcp-invoicenow-sg](https://github.com/cmendezs/mcp-invoicenow-sg) |
| 🇪🇸 Spanien | [mcp-facturacion-electronica-es](https://github.com/cmendezs/mcp-facturacion-electronica-es) |
| 🇦🇪 Vereinigte Arabische Emirate | [mcp-einvoicing-ae](https://github.com/cmendezs/mcp-einvoicing-ae) |

## Lizenz

Dieses Projekt steht unter der **Apache-2.0-Lizenz**. Einzelheiten finden Sie in der Datei [LICENSE](LICENSE). Die vollstaendige Versionshistorie finden Sie in [CHANGELOG.md](CHANGELOG.md).
