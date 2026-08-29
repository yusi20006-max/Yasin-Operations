from __future__ import annotations

import importlib.util

import pytest


mcp_available = importlib.util.find_spec("mcp") is not None
pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp extra is not installed")


def test_mcp_server_exports_expected_tools() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["mcp"])
    tools = module.mcp._tool_manager.list_tools()
    names = {tool.name for tool in tools}
    assert {
        "yasin_status",
        "yasin_health",
        "yasin_doctor",
        "yasin_start",
        "yasin_stop",
        "yasin_restart",
    } <= names


def test_mutation_requires_confirmation() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["_mutate"])
    result = module._mutate("restart", "demo", confirmation=False, dry_run=False)
    assert result["success"] is False
    assert result["error"]["category"] == "permission_denied"
    assert result["error"]["details"]["requires_confirmation"] is True
