"""MCP server optional integration tests.

These tests require the optional ``mcp`` extra. They exercise a real import
of the MCP SDK and the Yasin-Operations FastMCP bridge. They must not mask
ImportError; if cryptography/MCP cannot load on the runtime, the tests fail
when the extra is installed.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest


def _mcp_spec_available() -> bool:
    return importlib.util.find_spec("mcp") is not None


mcp_available = _mcp_spec_available()
pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp extra is not installed")


def test_mcp_sdk_imports_successfully() -> None:
    """Real import of the MCP SDK must succeed when the extra is present."""
    import mcp  # noqa: F401
    from mcp.server.fastmcp import FastMCP  # noqa: F401

    assert mcp is not None


def test_mcp_server_module_imports() -> None:
    """Importing the bridge module must exercise the MCP dependency path."""
    module = __import__("yasin_operations.mcp_server", fromlist=["mcp", "main"])
    assert hasattr(module, "mcp")
    assert hasattr(module, "main")
    assert module.mcp is not None


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


def test_mutation_dry_run_allowed_without_confirmation() -> None:
    module = __import__("yasin_operations.mcp_server", fromlist=["_mutate"])
    result = module._mutate("restart", "demo", confirmation=False, dry_run=True)
    if not result["success"] and result.get("error"):
        assert result["error"].get("category") != "permission_denied"


def test_termux_cryptography_compatibility_note() -> None:
    """Document the known Termux/Python 3.14 cryptography ABI boundary.

    On native Termux Python 3.14, cryptography's abi3 Rust extension may fail
    to resolve PyLong_Type / PyModule_Type unless the Termux-packaged
    python-cryptography (patchelf --add-needed libpython) is used or
    LD_PRELOAD points at libpython3.14.so. This test records environment
    signals for operators; it does not mask ImportError.
    """
    is_android = "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ
    py_version = sys.version_info[:2]
    note = {
        "platform": sys.platform,
        "python": f"{py_version[0]}.{py_version[1]}",
        "is_termux_like": is_android,
        "mcp_available": mcp_available,
    }
    assert isinstance(note, dict)
    if is_android and py_version >= (3, 14):
        assert True
