"""Real MCP client integration tests against the Yasin-Operations bridge."""
from __future__ import annotations

import asyncio
import importlib.util
import sys

import pytest

if importlib.util.find_spec("mcp") is None:
    pytest.skip("mcp extra is not installed", allow_module_level=True)

from mcp import Client, StdioServerParameters


EXPECTED_TOOLS = {
    "yasin_status",
    "yasin_health",
    "yasin_doctor",
    "yasin_monitor",
    "yasin_start",
    "yasin_stop",
    "yasin_restart",
}


def _run(coro):
    return asyncio.run(coro)


def test_in_process_client_discovers_expected_tools() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["mcp"])

    async def check() -> None:
        async with Client(module.mcp, raise_exceptions=True) as client:
            result = await client.list_tools()
            names = {tool.name for tool in result.tools}
            assert EXPECTED_TOOLS <= names
            assert client.server_info is not None

    _run(check())


def test_in_process_client_preserves_mutation_confirmation_boundary() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["mcp"])

    async def check() -> None:
        async with Client(module.mcp, raise_exceptions=True) as client:
            result = await client.call_tool(
                "yasin_restart",
                {"service": "demo", "confirmation": False, "dry_run": False},
            )
            assert result.is_error is False
            assert result.structured_content is not None
            assert result.structured_content["success"] is False
            assert result.structured_content["error"]["category"] == "permission_denied"

    _run(check())


def test_stdio_client_discovers_tools_and_denies_unconfirmed_mutation() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "yasin_operations.mcp_server"],
    )

    async def check() -> None:
        # Client accepts StdioServerParameters and manages the subprocess transport.
        async with Client(server, raise_exceptions=True) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert EXPECTED_TOOLS <= names

            result = await client.call_tool(
                "yasin_restart",
                {"service": "demo", "confirmation": False, "dry_run": False},
            )
            assert result.is_error is False
            assert result.structured_content is not None
            assert result.structured_content["success"] is False
            assert result.structured_content["error"]["category"] == "permission_denied"

    _run(check())
