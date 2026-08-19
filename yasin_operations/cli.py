"""Command-line interface for standalone Yasin-Operations operation control."""
from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

from yasin_operations.config.config import (
    InvalidConfigurationError,
    OperationsConfig,
    load_config,
)
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.logging.audit import InMemoryAuditRecorder
from yasin_operations.runtime.resources import snapshot as resource_snapshot
from yasin_operations.runtime.termux.diagnostics import detect_termux
from yasin_operations.runtime.termux.runit import RunitServiceBackend
from yasin_operations.runtime.tools import register_runtime_tools
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.registry.registry import ToolRegistry


MUTATING_COMMANDS = {"start", "stop", "restart"}
STATUS_EXIT_OK = 0
STATUS_EXIT_DEGRADED = 1
STATUS_EXIT_ERROR = 2
HEALTH_EXIT_OK = 0
HEALTH_EXIT_DEGRADED = 1
HEALTH_EXIT_UNHEALTHY = 2
DOCTOR_EXIT_OK = 0
DOCTOR_EXIT_DEGRADED = 1
CONFIG_EXIT_ERROR = 2
OPERATION_EXIT_ERROR = 2
SCHEMA_VERSION = 1


def build_runtime(
    config_overrides: dict[str, object] | None = None,
) -> tuple[Executor, OperationsConfig, InMemoryAuditRecorder]:
    config = load_config(config_overrides)
    inspector = __import__(
        "yasin_operations.runtime.local.process_backend",
        fromlist=["LocalProcessInspector"],
    ).LocalProcessInspector()
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
        config=config,
    )
    audit = InMemoryAuditRecorder()
    return (
        Executor(
            registry,
            policy=SafetyPolicy(timeout_seconds=config.execution_timeout_seconds),
            audit_recorder=audit,
        ),
        config,
        audit,
    )


def _add_global_options(parser: argparse.ArgumentParser, *, suppress_defaults: bool = False) -> None:
    default = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument("--json", action="store_true", dest="as_json", default=default, help="emit machine-readable JSON")
    parser.add_argument("--service-root", default=default, help="override the configured runit service root")
    parser.add_argument("--sv-path", default=default, help="override the configured sv executable path")
    parser.add_argument("--services", default=default, help="override the service registry (comma-separated names)")
    parser.add_argument("--timeout", type=float, default=default, help="override operation execution timeout in seconds")
    parser.add_argument("--startup-grace", type=float, default=default, help="override startup grace period in seconds")
    parser.add_argument(
        "--log-level",
        choices=sorted(OperationsConfig._VALID_LOG_LEVELS),
        default=default,
        help="override log level",
    )
    always_on = parser.add_mutually_exclusive_group()
    always_on.add_argument(
        "--always-on",
        dest="always_on",
        action="store_true",
        default=default,
        help="enable always-on behavior",
    )
    always_on.add_argument(
        "--no-always-on",
        dest="always_on",
        action="store_false",
        default=default,
        help="disable always-on behavior",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yasin-operations",
        description="Yasin-Operations control CLI",
    )
    _add_global_options(parser)
    parser.set_defaults(always_on=None)

    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="show configured service status")
    _add_global_options(status, suppress_defaults=True)
    health = sub.add_parser("health", help="show Operations health and resource state")
    _add_global_options(health, suppress_defaults=True)
    doctor = sub.add_parser("doctor", help="run non-invasive Termux/runit diagnostics")
    _add_global_options(doctor, suppress_defaults=True)

    for name in sorted(MUTATING_COMMANDS):
        command = sub.add_parser(name, help=f"{name} a configured service")
        _add_global_options(command, suppress_defaults=True)
        command.add_argument("service")
        command.add_argument("--confirm", action="store_true", help="confirm the mutating action")
        command.add_argument("--dry-run", action="store_true", help="show the plan without changing state")
    return parser


def _configuration_overrides(args: argparse.Namespace) -> dict[str, object]:
    overrides: dict[str, object] = {}
    mapping = {
        "service_root": getattr(args, "service_root", None),
        "sv_path": getattr(args, "sv_path", None),
        "execution_timeout_seconds": getattr(args, "timeout", None),
        "startup_grace_seconds": getattr(args, "startup_grace", None),
        "always_on": getattr(args, "always_on", None),
        "log_level": getattr(args, "log_level", None),
    }
    overrides.update({key: value for key, value in mapping.items() if value is not None})
    services = getattr(args, "services", None)
    if services is not None:
        overrides["service_names"] = tuple(
            sorted({name.strip() for name in services.split(",") if name.strip()})
        )
    return overrides


def _operation_for_command(command: str, service: str) -> Operation:
    return Operation(
        name=f"service_{command}",
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


def _service_summary(services: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts = {"running": 0, "stopped": 0, "degraded": 0, "failed": 0, "unknown": 0, "other": 0}
    for service in services:
        state = str(service.get("state", "unknown"))
        if state in counts:
            counts[state] += 1
        else:
            counts["other"] += 1
    total = len(services)
    if counts["failed"] or counts["unknown"] or counts["other"]:
        health = "unhealthy"
        exit_code = STATUS_EXIT_ERROR
    elif counts["degraded"] or counts["stopped"] or counts["running"] != total:
        health = "degraded"
        exit_code = STATUS_EXIT_DEGRADED
    else:
        health = "healthy"
        exit_code = STATUS_EXIT_OK
    return {"total": total, "counts": counts, "health": health, "exit_code": exit_code}


def _health_exit_code(health: dict[str, Any], service_summary: dict[str, Any]) -> int:
    status = str(health.get("status", "unknown"))
    if status in {"unhealthy", "timeout"} or service_summary["health"] == "unhealthy":
        return HEALTH_EXIT_UNHEALTHY
    if status in {"degraded", "unknown"} or service_summary["health"] == "degraded":
        return HEALTH_EXIT_DEGRADED
    return HEALTH_EXIT_OK


def _configuration_error(command: str, exc: InvalidConfigurationError, as_json: bool) -> int:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "success": False,
        "error": {"category": "configuration", "message": str(exc)},
    }
    _emit(payload, as_json)
    return CONFIG_EXIT_ERROR


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = str(args.command)
    as_json = bool(getattr(args, "as_json", False))
    try:
        executor, config, audit = build_runtime(_configuration_overrides(args))
    except InvalidConfigurationError as exc:
        return _configuration_error(command, exc, as_json)

    if command == "doctor":
        diagnostics = detect_termux(
            config.service_root,
            sv_path=config.sv_path,
            expected_services=config.service_names,
        )
        success = not diagnostics.issues
        result = {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "success": success,
            "termux": diagnostics.as_dict(),
            "resources": resource_snapshot().as_dict(),
            "configuration": {
                "service_root": config.service_root,
                "sv_path": config.sv_path,
                "service_names": list(config.service_names),
                "always_on": config.always_on,
                "execution_timeout_seconds": config.execution_timeout_seconds,
                "startup_grace_seconds": config.startup_grace_seconds,
                "log_level": config.log_level,
                "missing_services": list(config.missing_services()),
            },
            "error": None if success else {"category": "diagnostics", "message": "one or more diagnostics reported issues"},
        }
        _emit(result, as_json)
        return DOCTOR_EXIT_OK if success else DOCTOR_EXIT_DEGRADED

    if command == "status":
        result = executor.execute(
            Operation(
                name="list_services",
                target=OperationTarget(kind="service", identifier="*"),
                safety_class=SafetyClass.READ_ONLY,
            ),
            actor="cli",
            source="cli.status",
        )
        data = dict(result.data or {})
        services = list(data.get("services", []))
        summary = _service_summary(services)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "success": result.success,
            "data": {"services": services, "summary": summary},
            "error": _error(result),
        }
        _emit(payload, as_json)
        if not result.success:
            return STATUS_EXIT_ERROR
        return int(summary["exit_code"])

    if command == "health":
        health_result = executor.execute(
            Operation(
                name="health_check",
                target=OperationTarget(kind="self", identifier="runtime"),
                safety_class=SafetyClass.READ_ONLY,
            ),
            actor="cli",
            source="cli.health",
        )
        service_result = executor.execute(
            Operation(
                name="list_services",
                target=OperationTarget(kind="service", identifier="*"),
                safety_class=SafetyClass.READ_ONLY,
            ),
            actor="cli",
            source="cli.health.services",
        )
        health = dict(health_result.data or {})
        service_data = dict(service_result.data or {})
        services = list(service_data.get("services", []))
        service_summary = _service_summary(services)
        success = health_result.success and service_result.success
        payload = {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "success": success,
            "health": health,
            "services": {"items": services, "summary": service_summary},
            "resources": resource_snapshot().as_dict(),
            "error": _error(health_result) or _error(service_result),
        }
        _emit(payload, as_json)
        if not success:
            return HEALTH_EXIT_UNHEALTHY
        return _health_exit_code(health, service_summary)

    operation = _operation_for_command(command, args.service)
    result = executor.execute(
        operation,
        actor="cli",
        source=f"cli.{command}",
        confirmation=bool(args.confirm),
        dry_run=bool(args.dry_run),
    )
    _emit(
        {
            "schema_version": SCHEMA_VERSION,
            "command": command,
            "success": result.success,
            "operation_id": result.operation_id,
            "data": dict(result.data or {}),
            "error": _error(result),
            "audit_entries": len(audit.entries),
        },
        as_json,
    )
    return STATUS_EXIT_OK if result.success else OPERATION_EXIT_ERROR


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
