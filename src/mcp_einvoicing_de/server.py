"""MCP server entrypoint for mcp-einvoicing-de."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from mcp_einvoicing_de import __version__
from mcp_einvoicing_de.tools.datev_export import TOOL_DATEV_EXPORT, handle_datev_export
from mcp_einvoicing_de.tools.invoice_convert import TOOL_INVOICE_CONVERT, handle_invoice_convert
from mcp_einvoicing_de.tools.invoice_create import TOOL_INVOICE_CREATE, handle_invoice_create
from mcp_einvoicing_de.tools.invoice_parse import TOOL_INVOICE_PARSE, handle_invoice_parse
from mcp_einvoicing_de.tools.invoice_validate import TOOL_INVOICE_VALIDATE, handle_invoice_validate
from mcp_einvoicing_de.tools.peppol_check import TOOL_PEPPOL_CHECK, handle_peppol_check
from mcp_einvoicing_de.tools.peppol_send import TOOL_PEPPOL_SEND, handle_peppol_send
from mcp_einvoicing_de.tools.tax_rules import TOOL_TAX_RULES, handle_tax_rules

LOG_LEVEL = os.environ.get("EINVOICING_DE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

_ALL_TOOLS: list[types.Tool] = [
    TOOL_INVOICE_CREATE,
    TOOL_INVOICE_VALIDATE,
    TOOL_INVOICE_PARSE,
    TOOL_INVOICE_CONVERT,
    TOOL_PEPPOL_CHECK,
    TOOL_PEPPOL_SEND,
    TOOL_DATEV_EXPORT,
    TOOL_TAX_RULES,
]

_TOOL_HANDLERS: dict[str, Any] = {
    "invoice_create": handle_invoice_create,
    "invoice_validate": handle_invoice_validate,
    "invoice_parse": handle_invoice_parse,
    "invoice_convert": handle_invoice_convert,
    "peppol_check": handle_peppol_check,
    "peppol_send": handle_peppol_send,
    "datev_export": handle_datev_export,
    "tax_rules": handle_tax_rules,
}


def _build_server() -> Server:
    """Instantiate and wire the MCP server."""
    server = Server("mcp-einvoicing-de")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return _ALL_TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name!r}")
        logger.debug("Dispatching tool %r with args %r", name, arguments)
        return await handler(arguments)

    return server


async def _run() -> None:
    server = _build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-einvoicing-de",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    """CLI entrypoint registered in pyproject.toml."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
