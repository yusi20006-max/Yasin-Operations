"""MCP stdio bridge for Hermes control of Yasin-Operations."""
from __future__ import annotations

import importlib.util
from typing import Any, Callable, TypeVar

from yasin_operations.cli import build_runtime, _error, _service_summary
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.mcp_compat import mcp_runtime_support
from yasin_operations.runtime.resources import snapshot as resource_snapshot
from yasin_operations.runtime.monitoring import build_monitoring_snapshot
from yasin_operations.safety.classification import SafetyClass

_support = mcp_runtime_support()
_mcp_installed = importlib.util.find_spec("mcp") is not None

if _support.supported and _mcp_installed:
    from mcp.server.mcpserver import MCPServer

    mcp: Any = MCPServer("yasin-operations")
else:
    mcp = None

_F = TypeVar("_F", bound=Callable[..., Any])


def _tool() -> Callable[[_F], _F]:
    """Register an MCP tool on supported runtimes, otherwise keep import safe.

    MCPServer.tool is a decorator *factory*; it must be called as ``@mcp.tool()``.
    """
    if mcp is None:
        return lambda function: function
    return mcp.tool()


def _runtime() -> tuple[Any, Any]:
    executor, config, _audit = build_runtime()
    return executor, config


def _service_operation(command: str, service: str) -> Operation:
    return Operation(
        name=f"service_{command}",
        target=OperationTarget(kind="service", identifier=service),
        safety_class=SafetyClass.MUTATING,
    )


@_tool()
def yasin_status() -> dict[str, Any]:
    """Return the configured Yasin service states and aggregate health."""
    executor, _config = _runtime()
    result = executor.execute(
        Operation(
            name="list_services",
            target=OperationTarget(kind="service", identifier="*"),
            safety_class=SafetyClass.READ_ONLY,
        ),
        actor="hermes",
        source="mcp.yasin_status",
    )
    data = dict(result.data or {})
    services = list(data.get("services", []))
    return {
        "success": result.success,
        "services": services,
        "summary": _service_summary(services),
        "error": _error(result),
    }


@_tool()
def yasin_health() -> dict[str, Any]:
    """Return Yasin-Operations health, service state, and local resources."""
    executor, _config = _runtime()
    health = executor.execute(
        Operation(
            name="health_check",
            target=OperationTarget(kind="self", identifier="runtime"),
            safety_class=SafetyClass.READ_ONLY,
        ),
        actor="hermes",
        source="mcp.yasin_health",
    )
    services = executor.execute(
        Operation(
            name="list_services",
            target=OperationTarget(kind="service", identifier="*"),
            safety_class=SafetyClass.READ_ONLY,
        ),
        actor="hermes",
        source="mcp.yasin_health.services",
    )
    service_data = dict(services.data or {})
    service_list = list(service_data.get("services", []))
    return {
        "success": health.success and services.success,
        "health": health.data,
        "services": {"items": service_list, "summary": _service_summary(service_list)},
        "resources": resource_snapshot(),
        "error": _error(health) or _error(services),
    }


@_tool()
def yasin_doctor() -> dict[str, Any]:
    """Return Termux/runit diagnostics and local resource snapshot."""
    from yasin_operations.runtime.termux.diagnostics import detect_termux

    _, config = _runtime()
    diagnostics = detect_termux(
        config.service_root,
        sv_path=config.sv_path,
        expected_services=config.service_names,
    )
    return {
        "success": True,
        "termux": diagnostics.as_dict(),
        "resources": resource_snapshot(),
        "configuration": {
            "service_root": config.service_root,
            "sv_path": config.sv_path,
            "service_names": list(config.service_names),
        },
    }


@_tool()
def yasin_monitor() -> dict[str, Any]:
    """Return the canonical monitoring snapshot (status + health + doctor)."""
    from yasin_operations.runtime.termux.diagnostics import detect_termux

    executor, config = _runtime()
    health = executor.execute(
        Operation(
            name="health_check",
            target=OperationTarget(kind="self", identifier="runtime"),
            safety_class=SafetyClass.READ_ONLY,
        ),
        actor="hermes",
        source="mcp.yasin_monitor.health",
    )
    services = executor.execute(
        Operation(
            name="list_services",
            target=OperationTarget(kind="service", identifier="*"),
            safety_class=SafetyClass.READ_ONLY,
        ),
        actor="hermes",
        source="mcp.yasin_monitor.services",
    )
    service_data = dict(services.data or {})
    service_list = list(service_data.get("services", []))
    termux = detect_termux(
        config.service_root,
        sv_path=config.sv_path,
        expected_services=config.service_names,
    )
    snapshot = build_monitoring_snapshot(
        services=service_list,
        health=health.data if isinstance(health.data, dict) else None,
        diagnostics=termux.as_dict(),
        resources=resource_snapshot(),
        configuration={
            "service_root": config.service_root,
            "sv_path": config.sv_path,
            "service_names": list(config.service_names),
            "missing_services": list(config.missing_services()) if hasattr(config, "missing_services") else [],
        },
    )
    payload = snapshot.as_dict()
    payload["success"] = health.success and services.success
    if not payload["success"]:
        payload["error"] = _error(health) or _error(services)
    return payload


def _mutate(command: str, service: str, confirmation: bool, dry_run: bool) -> dict[str, Any]:
    if not confirmation and not dry_run:
        return {
            "success": False,
            "error": {
                "category": "permission_denied",
                "message": "mutating operation requires explicit confirmation",
                "details": {"requires_confirmation": True},
            },
        }
    if mcp is None:
        reason = _support.reason if not _support.supported else "mcp SDK extra is not installed"
        return {
            "success": False,
            "error": {
                "category": "unavailable_dependency",
                "message": reason,
                "details": {
                    "mcp_supported": _support.supported,
                    "mcp_installed": _mcp_installed,
                    "is_termux": _support.is_termux,
                },
            },
        }
    executor, _config = _runtime()
    result = executor.execute(
        _service_operation(command, service),
        actor="hermes",
        source=f"mcp.yasin_{command}",
        confirmation=confirmation,
        dry_run=dry_run,
    )
    return {
        "success": result.success,
        "operation_id": result.operation_id,
        "data": dict(result.data or {}),
        "error": _error(result),
    }


@_tool()
def yasin_start(service: str, confirmation: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """Start a configured Yasin service. Confirmation is required unless dry_run is true."""
    return _mutate("start", service, confirmation, dry_run)


@_tool()
def yasin_stop(service: str, confirmation: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """Stop a configured Yasin service. Confirmation is required unless dry_run is true."""
    return _mutate("stop", service, confirmation, dry_run)


@_tool()
def yasin_restart(service: str, confirmation: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """Restart a configured Yasin service. Confirmation is required unless dry_run is true."""
    return _mutate("restart", service, confirmation, dry_run)


def main() -> None:
    """Run the MCP server over stdio for local Hermes integration."""
    if mcp is None:
        reason = _support.reason if not _support.supported else "mcp SDK extra is not installed"
        raise RuntimeError(f"MCP bridge unavailable: {reason}")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
