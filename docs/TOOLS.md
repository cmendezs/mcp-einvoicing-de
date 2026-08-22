# Tool reference — `mcp_einvoicing_de`

This file is generated from the MCP server's tool registry by `scripts/gen_tool_reference.py`. Do not edit it by hand; run the script instead.

**Tools:** 18

## `check_document_type_id_in_codelist`

Check whether a (scheme, value) pair is a recognized Peppol document type identifier.

Requires EINVOICING_PEPPOL_CODELIST_DIR (see `list_participant_id_schemes`).
Searches all entries regardless of state, so a historical (deprecated
or removed) document type is still reported as found.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `scheme` | string | yes |  |  |
| `value` | string | yes |  |  |

## `check_participant_id_scheme_in_codelist`

Check whether a 4-digit ISO 6523 ICD code (e.g. "0208") is a recognized Peppol scheme.

Requires EINVOICING_PEPPOL_CODELIST_DIR (see `list_participant_id_schemes`).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `icd` | string | yes |  |  |

## `check_process_id_in_codelist`

Check whether a (scheme, value) pair is a recognized Peppol process identifier.

Requires EINVOICING_PEPPOL_CODELIST_DIR (see `list_participant_id_schemes`).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `scheme` | string | yes |  |  |
| `value` | string | yes |  |  |

## `datev_export`

Export a ZUGFeRD invoice to DATEV CSV format (EXTF 700, Buchungsstapel).

Produces a CSV file importable by DATEV Belegtransfer or DATEV
Rechnungswesen. Maps invoice line items to DATEV booking records with
configurable accounts.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `invoice` | object | yes |  | ZUGFeRDInvoice data to export. |
| `revenue_account` | string | no | `'8400'` | DATEV revenue account number (Erloskonto). Default: 8400 (SKR 03, 19% USt). |
| `receivable_account` | string | no | `'10000'` | DATEV receivable account number (Debitorenkonto). Default: 10000. |
| `consultant_number` | string | no | `'0'` | DATEV Beraternummer (consultant number). |
| `client_number` | string | no | `'1'` | DATEV Mandantennummer (client number). |
| `fiscal_year_start` | string | no | `''` | Fiscal year start date (YYYYMMDD). Defaults to Jan 1 of invoice year. |

## `get_peppol_codelist_version`

Report the OpenPeppol eDEC code list release version(s) currently configured locally.

_No parameters._

## `invoice_convert`

Convert a ZUGFeRD or XRechnung invoice to a different profile or syntax.

Supports ZUGFeRD profile upgrades and downgrades, ZUGFeRD <-> XRechnung
conversion, and cross-syntax CII <-> UBL transformation. Profile
downgrades may result in data loss; set allow_data_loss=True to permit
this.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `target_profile` | string | yes |  | One of: MINIMUM, BASIC_WL, BASIC, EN_16931, EXTENDED, XRECHNUNG. |
| `xml_content` | string | null | no | `None` | Raw XML string of the source invoice. |
| `xml_base64` | string | null | no | `None` | Base64-encoded XML bytes. |
| `target_syntax` | string | no | `'CII'` | Target syntax: 'CII' or 'UBL'. UBL is only valid for XRECHNUNG. |
| `allow_data_loss` | boolean | no | `False` | If True, allow profile downgrades that discard data. Discarded fields are listed in the output. If False and data loss would occur, the conversion is rejected. |

## `invoice_create`

Generate a ZUGFeRD 2.x or XRechnung 3.x invoice in XML (CII or UBL) format.

Supports all ZUGFeRD profiles: MINIMUM, BASIC_WL, BASIC, EN_16931, EXTENDED.
For XRechnung, set profile to XRECHNUNG and choose CII or UBL syntax.
When the buyer is a German VAT-registered business (DE-prefixed VAT id), the
Wachstumschancengesetz B2B mandate (effective 2025-01-01, §14 Abs. 2 UStG)
requires a structured EN 16931 invoice. Non-XML output is rejected unless
transitional_period_opt_in is set to True (allowed only 2025-2026 with the
buyer's written consent).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `invoice` | object | yes |  | Invoice data matching the ZUGFeRDInvoice schema. Set invoice.profile to XRECHNUNG to produce an XRechnung invoice. |
| `output_format` | string | no | `'xml'` | 'xml' (default) or 'pdf' (ZUGFeRD hybrid PDF/A-3). |
| `syntax` | string | no | `'CII'` | XML syntax: 'CII' (default) or 'UBL' (XRechnung only). |
| `pretty_print` | boolean | no | `True` | Pretty-print the XML output. |
| `transitional_period_opt_in` | boolean | no | `False` | Acknowledge the Wachstumschancengesetz transitional period (2025-2026) and explicitly permit non-XML output for a German VAT-registered buyer. Set to True only when the buyer has agreed in writing to receive PDF or another non-structured format. From 2027 the transitional grace ends for large businesses; from 2028 all B2B invoices to German VAT-registered buyers must be in a structured EN 16931 format. Source: §14 Abs. 2 UStG, Wachstumschancengesetz of 27 March 2024 (BGBl. I Nr. 108). |

## `invoice_parse`

Extract structured data from a ZUGFeRD 2.x or XRechnung 3.x invoice.

Accepts raw XML (CII or UBL), base64-encoded XML, or base64-encoded PDF
(ZUGFeRD hybrid — the XML is extracted from the PDF/A-3 attachment).
Returns a structured JSON object matching the invoice data model.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `xml_content` | string | null | no | `None` | Raw XML string. |
| `xml_base64` | string | null | no | `None` | Base64-encoded XML bytes. |
| `pdf_base64` | string | null | no | `None` | Base64-encoded PDF bytes. The tool will extract the embedded XML attachment (ZUGFeRD hybrid PDF/A-3). |
| `include_raw_xml` | boolean | no | `False` | Include the raw XML string in the response. |

## `invoice_validate`

Validate a ZUGFeRD 2.x or XRechnung 3.x invoice XML.

Checks against EN 16931 rules and German KoSIT Schematron rules
(BR-DE-* business rules). Returns a structured validation report with
errors and warnings. Supports all ZUGFeRD profiles (MINIMUM through
EXTENDED) and XRechnung (CII and UBL syntax). Profile and syntax are
auto-detected if not specified. By default this validator runs
entirely locally (Schematron only). Set cloud_validate=True (or
EINVOICING_DE_KOSIT_ENABLE=1) to opt in to sending the invoice XML to
a remote KoSIT endpoint. Doing so egresses the full invoice payload.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `xml_content` | string | null | no | `None` | Raw XML string of the invoice to validate. Provide either xml_content or xml_base64, not both. |
| `xml_base64` | string | null | no | `None` | Base64-encoded XML bytes of the invoice. |
| `profile` | string | null | no | `None` | Override profile detection. One of: MINIMUM, BASIC_WL, BASIC, EN_16931, EXTENDED, XRECHNUNG. If omitted, auto-detected from the XML GuidelineID. |
| `syntax` | string | null | no | `None` | Override syntax detection. One of: CII, UBL. If omitted, auto-detected from the XML root element namespace. |
| `cloud_validate` | boolean | no | `False` | Opt in to sending the invoice XML to a remote KoSIT endpoint (egresses the full invoice payload). Local Schematron only by default. |
| `use_local_only` | boolean | null | no | `None` | [Deprecated] Use cloud_validate instead. use_local_only=True is equivalent to cloud_validate=False, which is now the default; this alias is retained for one release and will be removed. |
| `kosit_strict` | boolean | no | `False` | If True, fail hard when the KoSIT cloud validator is unreachable instead of falling back to local Schematron. |
| `strict` | boolean | no | `True` | If True, warnings are also reported. If False, only errors are returned. |

## `list_document_type_ids`

List Peppol document type identifiers from the OpenPeppol eDEC code list.

Requires EINVOICING_PEPPOL_CODELIST_DIR (see `list_participant_id_schemes`).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `active_only` | boolean | no | `True` | When True (default), omit deprecated/removed entries. |

## `list_participant_id_schemes`

List Peppol participant identifier (ICD) schemes from the OpenPeppol eDEC code list.

Requires EINVOICING_PEPPOL_CODELIST_DIR to point at a local copy of
the eDEC "Participant Identifier Schemes" GeneriCode export (not
bundled with this package, no confirmed redistribution rights, see
`mcp_einvoicing_core.peppol.codelists` module docstring).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `active_only` | boolean | no | `True` | When True (default), omit deprecated/removed entries. |

## `list_process_ids`

List Peppol process identifiers from the OpenPeppol eDEC code list.

Requires EINVOICING_PEPPOL_CODELIST_DIR (see `list_participant_id_schemes`).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `active_only` | boolean | no | `True` | When True (default), omit deprecated/removed entries. |

## `list_spis_use_case_ids`

List Peppol SPIS use case identifiers from the OpenPeppol eDEC code list.

Requires EINVOICING_PEPPOL_CODELIST_DIR (see `list_participant_id_schemes`).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `active_only` | boolean | no | `True` | When True (default), omit deprecated/removed entries. |

## `peppol_get_service_endpoint`

Fetch the AS4 endpoint for a Peppol participant's document type.

Resolves the SMP hostname via DNS, then fetches service metadata for
*document_type_id*. If the SMP returns a redirect, the result's
`redirect_url` is set and `endpoint_url` is None; callers must not
follow more than one redirect hop (SMP 1.4.0 §3.2).

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `identifier` | string | yes |  | Peppol participant ID or adaptable national identifier. |
| `document_type_id` | string | no | `'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1'` | Peppol document type identifier URN (default: BIS Billing 3.0 invoice). |
| `environment` | string | no | `'production'` | "production" or "test". |

## `peppol_lookup_participant`

Check whether a business is registered on the Peppol network.

Performs a DNS-over-HTTPS U-NAPTR lookup followed by an SMP
service-group request to determine registration status and the list
of supported document type identifiers.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `identifier` | string | yes |  | Peppol participant ID ("<scheme>:<value>") or a bare national identifier this server knows how to adapt (e.g. a VAT number, if a national identifier adapter is configured). |
| `environment` | string | no | `'production'` | "production" or "test". |

## `peppol_send`

Send a UBL/CII invoice to a Peppol participant via AS4.

Looks up the recipient's AS4 endpoint (SMP), builds the ebMS3/AS4
envelope, and transmits it using the supplied signing credentials.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `invoice_xml_base64` | string | yes |  | Base64-encoded UBL or CII invoice XML. |
| `recipient_identifier` | string | yes |  | Peppol participant ID or adaptable national identifier of the receiver. |
| `sender_id` | string | yes |  | Peppol AP identifier of the sender. |
| `certificate_path` | string | yes |  | Path to the PEM-encoded signing certificate. |
| `private_key_path` | string | yes |  | Path to the PEM-encoded private key. |
| `private_key_password` | string | no | `''` | Optional password for the private key. |
| `document_type_id` | string | no | `'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1'` | Peppol document type identifier URN (default: BIS Billing 3.0 invoice). |
| `environment` | string | no | `'test'` | "production" or "test". |

## `resolve_peppol_dns`

Resolve the SMP hostname for a Peppol participant via DNS only.

Performs the raw U-NAPTR (SML) lookup without fetching the SMP
service group, useful for diagnosing whether a participant is
registered in the SML independently of SMP reachability.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `identifier` | string | yes |  | Peppol participant ID or adaptable national identifier. |
| `environment` | string | no | `'production'` | "production" or "test". |

## `tax_rules`

Query German VAT rules for e-invoicing.

Returns structured information about VAT rates (19%, 7%), VAT category
codes, reverse charge rules under §13b UStG, zero-rate and exemption
provisions (§4 UStG), intra-community supply rules, and VATEX exemption
reason codes. For use when building invoice creation logic or
validating VAT treatment.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | yes |  | What to look up. Examples: 'reverse_charge', 'rates', 'exemptions', 'kleinunternehmer', '13b', 'zero_rate', 'vatex_codes', or a free-text question about German VAT. |
| `context` | string | null | no | `None` | Optional context about the transaction, e.g. 'construction services' or 'intra-community supply'. Used to filter relevant rules. |
