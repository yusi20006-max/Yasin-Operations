"""Runtime compatibility boundary for the optional MCP integration."""
from __future__ import annotations

from dataclasses import dataclass
import os
import sys


@dataclass(frozen=True)
class MCPRuntimeSupport:
    """Describe whether the optional MCP bridge is supported on this runtime."""

    supported: bool
    is_termux: bool
    reason: str


def is_native_termux() -> bool:
    """Return True for the native Android/Termux Python environment."""
    if os.environ.get("TERMUX_VERSION") or os.environ.get("ANDROID_ROOT"):
        return True
    prefix = os.environ.get("PREFIX", "")
    return prefix.startswith("/data/data/com.termux/files/")


def mcp_runtime_support() -> MCPRuntimeSupport:
    """Return the enforced support boundary for the optional MCP bridge.

    Native Termux Python 3.14 is intentionally outside the MCP support
    boundary while the upstream/Termux cryptography ABI issue remains
    unresolved. Core Yasin-Operations is unaffected because MCP is optional.
    """
    termux = is_native_termux()
    if termux and sys.version_info >= (3, 14):
        return MCPRuntimeSupport(
            supported=False,
            is_termux=True,
            reason=(
                "native Termux Python 3.14+ is not currently supported for the "
                "optional MCP bridge because cryptography's Rust abi3 extension "
                "can fail to resolve CPython symbols under Android/Bionic; "
                "use a supported Linux/proot MCP runtime until the underlying "
                "Termux dependency/runtime fix is available"
            ),
        )
    return MCPRuntimeSupport(supported=True, is_termux=termux, reason="supported runtime")
