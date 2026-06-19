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
└── Tools: create / validate / parse / convert / peppol_check / tax_rules

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

---

## ⚙️ Konfiguration

Der Server benötigt in v0.1.0 keine externen Zugangsdaten. Verfügbare Umgebungsvariablen:

| Variable | Beschreibung | Standard |
|----------|-------------|---------|
| `EINVOICING_DE_LOG_LEVEL` | Protokollierungsgrad (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `EINVOICING_DE_KOSIT_VALIDATOR_URL` | URL des KoSIT-Validierungstools (optional, für Remote-Validierung) | |
| `EINVOICING_DE_PEPPOL_SMP_URL` | Peppol-SMP-Lookup-URL (optional) | |
| `EINVOICING_DE_PDF_ENGINE` | PDF-Generierungsmodul (`reportlab` oder `pymupdf`) | `reportlab` |

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
| `invoice_create` | ZUGFeRD- oder XRechnung-XML (CII oder UBL) erzeugen; PDF/A-3-Hybrid geplant (v0.2.0) |
| `invoice_validate` | Rechnung gegen EN 16931 und KoSIT-Schematron-Regeln (BR-DE-\*) prüfen |
| `invoice_parse` | Strukturierte Daten aus einer bestehenden ZUGFeRD- oder XRechnung-Datei extrahieren |
| `invoice_convert` | Zwischen ZUGFeRD-Profilen oder ZUGFeRD ↔ XRechnung konvertieren |
| `peppol_check` | Peppol-Teilnehmerregistrierung eines deutschen Unternehmens prüfen (AS4) |
| `tax_rules` | Deutsche Umsatzsteuerregeln abfragen (Steuerklassen, §13b UStG, Befreiungen) |

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
| ZUGFeRD | 2.3 | MINIMUM, BASIC WL, BASIC, EN 16931, EXTENDED |
| XRechnung | 3.x | CII (Cross Industry Invoice), UBL (Universal Business Language) |
| EN 16931 | | Europäisches Kerndatenmodell für die elektronische Rechnung |
| Peppol BIS | 3.0 | Billing 3.0 (DE PINT) |

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

| Version | Funktionen |
|---------|-----------|
| **v0.1.0** (aktuell) | Werkzeuge: create, validate, parse, convert, peppol_check, tax_rules |
| **v0.2.0** | PDF/A-3-Einbettung (ZUGFeRD-Hybrid) via `reportlab` / `PyMuPDF` |
| **v0.3.0** | KoSIT-Online-Validator vollständig integriert |
| **v0.4.0** | Peppol AS4 Direktübermittlung |
| **v0.5.0** | DATEV-Exportformat |
| **v1.0.0** | Produktionsreif, vollständige EN 16931-Abdeckung |

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

## Other e-invoicing MCP servers

| Country | Server |
|---------|--------|
| 🌍 Global | [mcp-einvoicing-core](https://github.com/cmendezs/mcp-einvoicing-core) |
| 🇧🇪 Belgium | [mcp-einvoicing-be](https://github.com/cmendezs/mcp-einvoicing-be) |
| 🇧🇷 Brazil | [mcp-nfe-br](https://github.com/cmendezs/mcp-nfe-br) |
| 🇫🇷 France | [mcp-facture-electronique-fr](https://github.com/cmendezs/mcp-facture-electronique-fr) |
| 🇩🇪 Germany | [mcp-einvoicing-de](https://github.com/cmendezs/mcp-einvoicing-de) |
| 🇮🇹 Italy | [mcp-fattura-elettronica-it](https://github.com/cmendezs/mcp-fattura-elettronica-it) |
| 🇵🇱 Poland | [mcp-ksef-pl](https://github.com/cmendezs/mcp-ksef-pl) |
| 🇪🇸 Spain | [mcp-facturacion-electronica-es](https://github.com/cmendezs/mcp-facturacion-electronica-es) |

---

## 📄 Lizenz

Dieses Projekt steht unter der **Apache-2.0-Lizenz**.  
Einzelheiten finden Sie in der Datei [LICENSE](LICENSE).

Copyright 2026 cmendezs

---

*Projekt gepflegt von [cmendezs](https://github.com/cmendezs). Für Fragen zur Implementierung der ZUGFeRD- oder XRechnung-Spezifikation bitte ein Issue eröffnen.*
