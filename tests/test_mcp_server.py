"""MCP server optional integration and Termux boundary tests."""
from __future__ import annotations

import importlib.util

import pytest

from yasin_operations.mcp_compat import mcp_runtime_support


def _mcp_spec_available() -> bool:
    return importlib.util.find_spec("mcp") is not None


mcp_available = _mcp_spec_available()
mcp_support = mcp_runtime_support()
mcp_functional = pytest.mark.skipif(
    not mcp_available or not mcp_support.supported,
    reason=(
        "MCP functional path is unavailable on this runtime: "
        f"{mcp_support.reason}"
    ),
)


def test_termux_python_314_boundary_is_explicit() -> None:
    """Native Termux Python 3.14+ must use the documented MCP boundary."""
    if mcp_support.is_termux:
        assert mcp_support.supported is False or mcp_support.reason == "supported runtime"
    if mcp_support.is_termux and mcp_support.supported is False:
        assert "Termux Python 3.14" in mcp_support.reason
        assert "LD_PRELOAD" not in mcp_support.reason


@mcp_functional
def test_mcp_sdk_imports_successfully() -> None:
    """Real import of the MCP SDK must succeed on a supported runtime."""
    import mcp  # noqa: F401
    from mcp.server.mcpserver import MCPServer  # noqa: F401

    assert mcp is not None


@mcp_functional
def test_mcp_server_module_imports() -> None:
    """Importing the bridge module must exercise the MCP dependency path."""
    module = __import__("yasin_operations.mcp_server", fromlist=["mcp", "main"])
    assert hasattr(module, "mcp")
    assert hasattr(module, "main")
    assert module.mcp is not None


@mcp_functional
def test_mcp_server_exports_expected_tools() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["mcp"])
    tools = module.mcp._tool_manager.list_tools()
    names = {tool.name for tool in tools}
    assert {
        "yasin_status",
        "yasin_health",
        "yasin_doctor",
        "yasin_monitor",
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


@mcp_functional
def test_mutation_dry_run_allowed_without_confirmation() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["_mutate"])
    result = module._mutate("restart", "demo", confirmation=False, dry_run=True)
    if not result["success"] and result.get("error"):
        assert result["error"].get("category") != "permission_denied"
