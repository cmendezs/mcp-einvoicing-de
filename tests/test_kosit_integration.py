"""DE-V1-5: End-to-end KoSIT integration test.

Network-dependent test that submits one invoice per profile to
https://validator.kosit.de and asserts valid: true.
Gated behind EINVOICING_DE_INTEGRATION_TESTS=1. Runs nightly, not on every PR.
"""

from __future__ import annotations

import json
import os

import pytest

from mcp_einvoicing_de.tools.invoice_validate import handle_invoice_validate

_INTEGRATION = os.environ.get("EINVOICING_DE_INTEGRATION_TESTS") == "1"
pytestmark = pytest.mark.skipif(not _INTEGRATION, reason="Integration tests disabled")


@pytest.fixture()
def en16931_xml(minimal_invoice: object) -> str:
    from mcp_einvoicing_de.models.zugferd import ZUGFeRDProfile
    from mcp_einvoicing_de.serializers import ZUGFeRDCIISerializer

    invoice = minimal_invoice.model_copy(update={"profile": ZUGFeRDProfile.EN_16931})  # type: ignore[union-attr]
    xml_bytes = ZUGFeRDCIISerializer().serialize(invoice, pretty_print=True)  # type: ignore[arg-type]
    return xml_bytes.decode("utf-8")


class TestKoSITIntegration:
    @pytest.mark.asyncio
    async def test_kosit_cloud_validates_en16931(self, en16931_xml: str) -> None:
        result = await handle_invoice_validate(
            {"xml_content": en16931_xml, "kosit_strict": True}
        )
        data = json.loads(result[0].text)
        assert data["validator_used"] == "kosit_cloud", (
            f"Expected kosit_cloud but got {data['validator_used']}"
        )
        assert data["is_valid"], (
            f"KoSIT validation failed: {data.get('errors', [])}"
        )
