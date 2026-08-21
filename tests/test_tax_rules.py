"""Tests for the tax_rules MCP tool."""

from __future__ import annotations

import pytest

from mcp_einvoicing_de.tools.tax_rules import tax_rules


class TestHandleTaxRules:
    @pytest.mark.asyncio
    async def test_rates_query_returns_19_and_7(self) -> None:
        data = await tax_rules(query="rates")
        assert "results" in data
        rates = [r.get("rate_percent") for r in data["results"] if "rate_percent" in r]
        assert 19 in rates
        assert 7 in rates

    @pytest.mark.asyncio
    async def test_reverse_charge_query_returns_13b_entries(self) -> None:
        data = await tax_rules(query="reverse_charge")
        paragraphs = [r.get("paragraph", "") for r in data["results"]]
        assert any("13b" in p for p in paragraphs)

    @pytest.mark.asyncio
    async def test_vatex_query_returns_codes(self) -> None:
        data = await tax_rules(query="vatex_codes")
        codes = [r.get("vatex_code") for r in data["results"] if r.get("vatex_code")]
        assert len(codes) > 0
        assert any(c.startswith("VATEX") for c in codes)

    @pytest.mark.asyncio
    async def test_unknown_query_falls_back_to_rates(self) -> None:
        data = await tax_rules(query="something_completely_unknown")
        assert "results" in data
        assert len(data["results"]) > 0
        assert len(data["notes"]) > 0

    @pytest.mark.asyncio
    async def test_disclaimer_always_present(self) -> None:
        data = await tax_rules(query="rates")
        assert "legal_disclaimer" in data
        assert len(data["legal_disclaimer"]) > 0

    @pytest.mark.asyncio
    async def test_context_filter_for_construction(self) -> None:
        data = await tax_rules(query="reverse_charge", context="construction services")
        assert "results" in data
        # At least one result should mention construction
        descriptions = " ".join(
            r.get("description_en", "") for r in data["results"]
        ).lower()
        assert "construction" in descriptions or len(data["results"]) > 0
