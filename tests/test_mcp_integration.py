"""End-to-end MCP client/bridge integration tests.

The tests are optional because MCP is an optional dependency. When MCP is
installed they intentionally exercise the real MCP SDK client, including the
stdio subprocess transport used by Hermes-style hosts.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys

import pytest


if importlib.util.find_spec("mcp") is None:
    pytest.skip("mcp extra is not installed", allow_module_level=True)

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_TOOLS = {
    "yasin_status",
    "yasin_health",
    "yasin_doctor",
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
        async with stdio_client(server) as transport:
            async with Client(transport, raise_exceptions=True) as client:
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
