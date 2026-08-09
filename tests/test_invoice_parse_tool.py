"""Regression test: handle_invoice_parse must not leak IBAN/BIC to the LLM.

The MCP tool response (invoice_data + raw_xml) is text an LLM reads directly.
mcp_einvoicing_core.base_server.scrub() must redact IBAN/BIC before either
field is returned, per the P1.5 output-masking layer.
"""

from __future__ import annotations

import asyncio
import json

from mcp_einvoicing_de.serializers import ZUGFeRDCIISerializer
from mcp_einvoicing_de.tools.invoice_parse import handle_invoice_parse


def test_invoice_parse_redacts_iban_and_bic(minimal_invoice) -> None:
    xml_bytes = ZUGFeRDCIISerializer().serialize(minimal_invoice, pretty_print=False)

    result = asyncio.run(
        handle_invoice_parse(
            {"xml_content": xml_bytes.decode("utf-8"), "include_raw_xml": True}
        )
    )
    payload = json.loads(result[0].text)

    assert "DE89370400440532013000" not in json.dumps(payload)
    assert "COBADEFFXXX" not in json.dumps(payload)
    assert "[IBAN REDACTED]" in json.dumps(payload["invoice_data"])
    assert "[BIC REDACTED]" in json.dumps(payload["invoice_data"])
    assert "[IBAN REDACTED]" in payload["raw_xml"]
