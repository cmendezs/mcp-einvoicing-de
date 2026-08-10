# mcp-einvoicing-de 🇩🇪

[English](README.md) | [Deutsch](README.de.md)

<!-- mcp-name: io.github.cmendezs/mcp-einvoicing-de -->

![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)
[![PyPI version](https://img.shields.io/pypi/v/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-einvoicing-de.svg)](https://pypi.org/project/mcp-einvoicing-de/)
[![mcp-einvoicing-de MCP server](https://glama.ai/mcp/servers/cmendezs/mcp-einvoicing-de/badges/score.svg)](https://glama.ai/mcp/servers/cmendezs/mcp-einvoicing-de)

MCP-Server (Model Context Protocol) in Python für die **deutsche elektronische Rechnung** in den Formaten **ZUGFeRD 2.x** und **XRechnung 3.x** (EN 16931, FeRD, KoSIT). Ermöglicht KI-Agenten (Claude, IDEs) das Erstellen, Validieren, Parsen und Konvertieren von E-Rechnungen, die vollständig dem deutschen B2B-E-Rechnungsmandat (gültig ab 2025, schrittweise Durchsetzung bis 2027 bis 2028) und der europäischen Norm EN 16931 entsprechen.

---

## 🏗️ Aufgebaut auf

Dieses Paket basiert auf [**mcp-einvoicing-core**](https://github.com/cmendezs/mcp-einvoicing-core), einer gemeinsamen Basisbibliothek für europäische E-Rechnungs-MCP-Server. Sie stellt gemeinsame Modelle, Validierungsabstraktionen, XML-Hilfsfunktionen und die Ausnahmehierarchie bereit.

`mcp-einvoicing-core` wird automatisch als transitive Abhängigkeit installiert, kein zusätzlicher Schritt erforderlich.

> **Für Entwickler:** `pip install -e ".[dev]"` installiert das Basispaket automatisch aus PyPI.

---

## 🏗️ Architektur

```
mcp-einvoicing-de (dieses Paket, eigenständiger MCP-Server)
├── ZUGFeRDInvoice / XRechnungInvoice  ← Pydantic-Modelle (alle Profile)
├── SchematronValidator                ← EN 16931 + KoSIT BR-DE-* Regeln
├── KoSITValidator                     ← Remote-Validierungstool (optional)
└── Tools: create / validate / parse / convert / peppol_check / peppol_send / datev_export / tax_rules

        ↑ erweitert
mcp-einvoicing-core (gemeinsame Basis, als Abhängigkeit installiert)
├── BaseDocumentGenerator / Validator / Parser
├── BaseInvoice, BaseParty … (Pydantic)
├── xml_utils, exceptions
└── EInvoicingMCPServer
```

---

## 🚀 Installation

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

---

## ⚙️ Konfiguration

Der Server benötigt keine externen Zugangsdaten. Verfügbare Umgebungsvariablen:

| Variable | Beschreibung | Standard |
|----------|-------------|---------|
| `EINVOICING_DE_LOG_LEVEL` | Protokollierungsgrad (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `EINVOICING_DE_KOSIT_VALIDATOR_URL` | URL eines selbst gehosteten KoSIT-Validierungstool-REST-Endpunkts. Wird nur verwendet, wenn die Cloud-Validierung aktiviert ist — siehe `EINVOICING_DE_KOSIT_ENABLE` | |
| `EINVOICING_DE_KOSIT_ENABLE` | Auf `1` setzen, um die KoSIT-Cloud-Validierung zu aktivieren (`validator.kosit.de` oder ein selbst gehosteter Endpunkt). Standardmaessig laeuft nur lokales Schematron | |
| `EINVOICING_DE_PEPPOL_CERT_PATH` | Pfad zum X.509-Zertifikat fuer die Peppol-AS4-Signierung (PEM oder DER) | |
| `EINVOICING_DE_PEPPOL_KEY_PATH` | Pfad zum privaten Schluessel fuer die Peppol-AS4-Signierung (PEM oder DER) | |
| `EINVOICING_DE_PEPPOL_KEY_PASSWORD` | Passwort fuer den privaten Schluessel (falls verschluesselt) | |

### 🤖 Integration Claude Desktop

Eintrag in die Datei `claude_desktop_config.json`:

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

### ⌨️ Integration Cursor

Konfigurationsdatei (`~/.cursor/mcp.json` oder `.cursor/mcp.json` im Projektverzeichnis):

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

### 🪐 Integration Kiro

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

---

## 🧰 Verfügbare MCP-Werkzeuge

| Werkzeug | Beschreibung |
|----------|-------------|
| `invoice_create` | ZUGFeRD- oder XRechnung-XML (CII oder UBL) erzeugen. Erzwingt das B2B-Mandat nach §14 Abs. 2 UStG: Nicht-XML-Ausgaben werden fuer deutsche Rechnungsempfaenger mit USt-IdNr. (DE-Praefix) abgelehnt, sofern nicht `transitional_period_opt_in=True` gesetzt ist. `output_format='pdf'` erzeugt eine PDF/A-3-Hybridrechnung der Stufe B mit sRGB-ICC-Profil, OutputIntent, eingebetteten Schriften und deterministischer /ID. |
| `invoice_validate` | Rechnung gegen EN 16931 und KoSIT-Regeln (BR-DE-\*) pruefen. Standardmaessig laeuft nur lokale Schematron-Validierung (es verlassen keine Daten den eigenen Rechner); mit `cloud_validate=True` oder `EINVOICING_DE_KOSIT_ENABLE=1` die KoSIT-Cloud-Validierung (`validator.kosit.de` oder ein selbst gehosteter Endpunkt) mit exponentiellem Backoff-Retry (1s/2s/4s) aktivieren. Lokale XSLT-2.0-Validierung erfordert das Extra `[xslt2]`. |
| `invoice_parse` | Strukturierte Daten aus ZUGFeRD- oder XRechnung-XML extrahieren oder aus einer PDF/A-3-Hybridrechnung mit eingebetteter `factur-x.xml` / `zugferd-invoice.xml`. |
| `invoice_convert` | Zwischen ZUGFeRD-Profilen konvertieren, ZUGFeRD/XRechnung-CII-Header tauschen oder Cross-Syntax-Konvertierung CII/UBL ueber Core `convert_wire_format` durchfuehren. |
| `peppol_check` | Peppol-Teilnehmerregistrierung eines deutschen Unternehmens ueber SMP/SML-Lookup pruefen. |
| `peppol_send` | Rechnung an einen Peppol-Empfaenger per AS4-Ausgansuebermittlung senden. Konvertiert ZUGFeRD zu XRechnung UBL (Peppol BIS 3.0 Profil), signiert mit X.509-Zugangsdaten und gibt die AS4-Empfangsbestaetigung zurueck. Erfordert `EINVOICING_DE_PEPPOL_CERT_PATH` und `EINVOICING_DE_PEPPOL_KEY_PATH`. |
| `datev_export` | ZUGFeRD-Rechnung als DATEV-EXTF-700-Buchungsstapel-CSV-Datei fuer den Import in DATEV-Buchhaltungssoftware exportieren. Standardmaessig SKR-03-Konten (8400 Erloese / 10000 Forderungen). |
| `tax_rules` | Deutsche Umsatzsteuerregeln abfragen (Saetze, §13b-UStG-Reverse-Charge-Codes, §19-UStG-Kleinunternehmerschwellen nach JStG 2024 mit 25.000 EUR Vorjahr / 100.000 EUR laufendes Jahr, Befreiungen). |

---

## Verwendungsbeispiele

### Beispiel 1: Rechnung validieren

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

### Beispiel 2: Deutsche Steuerregeln abfragen

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

### Beispiel 3: Peppol-Registrierung prüfen

```
3. peppol_check(
     participant_id="0204:991-1234512345-06",
     environment="production"
   )
   → {
       "is_registered": true,
       "participant_id": "0204:991-1234512345-06",
       "document_type_supported": true,
       "access_point_url": "https://ap.example.de/as4",
       "transport_profile": "peppol-transport-as4-v2.0"
     }
```

### Beispiel 4: Rechnungsdaten parsen

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

---

## 📚 Unterstützte Standards

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

---

## 🧪 Tests

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

---

## Roadmap

Aktuelle Version: **v0.8.0**.

Die Historie frueherer Releases finden Sie in [RELEASE.md](RELEASE.md).

---

## Mitwirken

Beiträge sind willkommen. Bitte öffnen Sie ein Issue, bevor Sie einen Pull Request für wesentliche Änderungen einreichen.

```bash
git clone https://github.com/cmendezs/mcp-einvoicing-de.git
cd mcp-einvoicing-de
pip install -e ".[dev]"
pytest
make audit
```

---

## Weitere MCP-Server für E-Rechnungen

| Land | Server |
|------|--------|
| 🌍 Global | [mcp-einvoicing-core](https://github.com/cmendezs/mcp-einvoicing-core) |
| 🇧🇪 Belgien | [mcp-einvoicing-be](https://github.com/cmendezs/mcp-einvoicing-be) |
| 🇧🇷 Brasilien | [mcp-nfe-br](https://github.com/cmendezs/mcp-nfe-br) |
| 🇫🇷 Frankreich | [mcp-facture-electronique-fr](https://github.com/cmendezs/mcp-facture-electronique-fr) |
| 🇩🇪 Deutschland | [mcp-einvoicing-de](https://github.com/cmendezs/mcp-einvoicing-de) |
| 🇮🇹 Italien | [mcp-fattura-elettronica-it](https://github.com/cmendezs/mcp-fattura-elettronica-it) |
| 🇵🇱 Polen | [mcp-ksef-pl](https://github.com/cmendezs/mcp-ksef-pl) |
| 🇪🇸 Spanien | [mcp-facturacion-electronica-es](https://github.com/cmendezs/mcp-facturacion-electronica-es) |

---

## 📄 Lizenz

Dieses Projekt steht unter der **Apache-2.0-Lizenz**.  
Einzelheiten finden Sie in der Datei [LICENSE](LICENSE).

Copyright 2026 cmendezs

---

*Projekt gepflegt von [cmendezs](https://github.com/cmendezs). Für Fragen zur Implementierung der ZUGFeRD- oder XRechnung-Spezifikation bitte ein Issue eröffnen.*
