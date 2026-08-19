"""Command-line interface for standalone Yasin-Operations operation control."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from yasin_operations.config.config import OperationsConfig
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.logging.audit import InMemoryAuditRecorder
from yasin_operations.runtime.resources import snapshot as resource_snapshot
from yasin_operations.runtime.termux.config import TermuxRuntimeConfig
from yasin_operations.runtime.termux.diagnostics import detect_termux
from yasin_operations.runtime.termux.runit import RunitServiceBackend
from yasin_operations.runtime.tools import register_runtime_tools
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.registry.registry import ToolRegistry


MUTATING_COMMANDS = {"start", "stop", "restart"}


def build_runtime() -> tuple[Executor, TermuxRuntimeConfig, InMemoryAuditRecorder]:
    config = TermuxRuntimeConfig.from_env()
    inspector = __import__("yasin_operations.runtime.local.process_backend", fromlist=["LocalProcessInspector"]).LocalProcessInspector()
    backend = RunitServiceBackend(
        inspector,
        service_root=config.service_root,
        definitions=config.service_definitions(),
        timeout=config.execution_timeout_seconds,
        sv_path=config.sv_path,
    )
    registry = ToolRegistry()
    register_runtime_tools(
        registry,
        inspector=inspector,
        service_backend=backend,
        config=OperationsConfig(execution_timeout_seconds=int(config.execution_timeout_seconds)),
    )
    audit = InMemoryAuditRecorder()
    return Executor(registry, policy=SafetyPolicy(timeout_seconds=config.execution_timeout_seconds), audit_recorder=audit), config, audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yasin-operations", description="Yasin-Operations control CLI")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show configured service status")
    sub.add_parser("health", help="show Operations health and resource state")
    sub.add_parser("doctor", help="run Termux/runit startup diagnostics")
    for name in sorted(MUTATING_COMMANDS):
        command = sub.add_parser(name, help=f"{name} a configured service")
        command.add_argument("service")
        command.add_argument("--confirm", action="store_true", help="confirm the mutating action")
        command.add_argument("--dry-run", action="store_true", help="show the plan without changing state")
    return parser


def _operation_for_command(command: str, service: str) -> Operation:
    operation = f"service_{command}"
    return Operation(
        name=operation,
        target=OperationTarget(kind="service", identifier=service),
        safety_class=SafetyClass.MUTATING,
    )


def _emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    elif isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}: {item}")
    else:
        print(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    executor, config, audit = build_runtime()

    if args.command == "doctor":
        diagnostics = detect_termux(config.service_root)
        result = {
            "termux": diagnostics.as_dict(),
            "resources": resource_snapshot().as_dict(),
            "configuration": {
                "service_root": config.service_root,
                "sv_path": config.sv_path,
                "service_names": list(config.service_names),
                "always_on": config.always_on,
            },
        }
        _emit(result, args.as_json)
        return 0 if not diagnostics.issues else 1

    if args.command == "status":
        result = executor.execute(
            Operation(
                name="list_services",
                target=OperationTarget(kind="service", identifier="*"),
                safety_class=SafetyClass.READ_ONLY,
            ),
            actor="cli",
            source="cli.status",
        )
        _emit({"success": result.success, "data": dict(result.data or {}), "error": _error(result)}, args.as_json)
        return 0 if result.success else 2

    if args.command == "health":
        health = executor.execute(
            Operation(
                name="health_check",
                target=OperationTarget(kind="self", identifier="runtime"),
                safety_class=SafetyClass.READ_ONLY,
            ),
            actor="cli",
            source="cli.health",
        )
        _emit(
            {
                "success": health.success,
                "health": dict(health.data or {}),
                "resources": resource_snapshot().as_dict(),
                "error": _error(health),
            },
            args.as_json,
        )
        return 0 if health.success else 2

    operation = _operation_for_command(args.command, args.service)
    result = executor.execute(
        operation,
        actor="cli",
        source=f"cli.{args.command}",
        confirmation=bool(args.confirm),
        dry_run=bool(args.dry_run),
    )
    _emit(
        {
            "success": result.success,
            "operation_id": result.operation_id,
            "data": dict(result.data or {}),
            "error": _error(result),
            "audit_entries": len(audit.entries),
        },
        args.as_json,
    )
    return 0 if result.success else 2


def _error(result: Any) -> dict[str, Any] | None:
    if result.error is None:
        return None
    return {
        "category": result.error.category.value,
        "message": result.error.message,
        "details": dict(result.error.details),
    }


if __name__ == "__main__":
    raise SystemExit(main())
