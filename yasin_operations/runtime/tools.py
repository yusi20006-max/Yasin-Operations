"""Core Tool adapters for Runtime Operations.

These tools translate typed Operations into calls to the runtime
contracts. They contain no shell interface and never accept arbitrary
commands.
"""
from __future__ import annotations

import os
import platform
import sys
import time
from typing import Any

from yasin_operations.config.config import OperationsConfig
from yasin_operations.core.operations.models import Operation
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.runtime.diagnostics import DiagnosticsSnapshot
from yasin_operations.runtime.health import HealthCheckResult, HealthStatus
from yasin_operations.runtime.local.process_backend import LocalProcessInspector
from yasin_operations.runtime.local.service_backend import LocalServiceBackend
from yasin_operations.runtime.process import InvalidPIDError, ProcessInspector, ProcessNotFoundError
from yasin_operations.runtime.service import ServiceBackend, ServiceNotFoundError
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import Tool, ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class ProcessTool:
    def __init__(self, inspector: ProcessInspector | None = None) -> None:
        self.inspector = inspector or LocalProcessInspector()
        self._descriptor = ToolDescriptor(
            id="runtime.process",
            description="Read-only local process inspection",
            capabilities=(
                ToolCapability("list_processes", SafetyClass.READ_ONLY),
                ToolCapability("find_process", SafetyClass.READ_ONLY),
                ToolCapability("process_status", SafetyClass.READ_ONLY),
                ToolCapability("process_alive", SafetyClass.READ_ONLY),
            ),
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        try:
            if operation.name == "list_processes":
                return OperationResult.ok(
                    operation.id,
                    {"processes": [self._as_dict(p) for p in self.inspector.list_processes()]},
                )
            if operation.name == "find_process":
                pattern = str(operation.parameters.get("pattern", operation.target.identifier))
                return OperationResult.ok(
                    operation.id,
                    {"processes": [self._as_dict(p) for p in self.inspector.find_by_name(pattern)]},
                )
            pid = self._pid(operation)
            if operation.name == "process_status":
                return OperationResult.ok(operation.id, self._as_dict(self.inspector.get_process(pid)))
            if operation.name == "process_alive":
                return OperationResult.ok(operation.id, {"pid": pid, "alive": self.inspector.is_alive(pid)})
            return OperationResult.fail(
                operation.id,
                OperationError(ErrorCategory.UNSUPPORTED_OPERATION, f"Unsupported process operation: {operation.name!r}"),
            )
        except InvalidPIDError as exc:
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.VALIDATION_ERROR, str(exc)))
        except ProcessNotFoundError as exc:
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.EXECUTION_FAILURE, str(exc)))
        except Exception as exc:  # noqa: BLE001
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.INTERNAL_ERROR, str(exc)))

    @staticmethod
    def _pid(operation: Operation) -> int:
        value: Any = operation.parameters.get("pid", operation.target.identifier)
        try:
            return int(value)
        except (TypeError, ValueError):
            raise InvalidPIDError(value) from None

    @staticmethod
    def _as_dict(process: Any) -> dict[str, Any]:
        return {
            "pid": process.pid,
            "name": process.name,
            "status": process.status,
            "ppid": process.ppid,
            "username": process.username,
            "cmdline": process.cmdline,
            "memory_rss_bytes": process.memory_rss_bytes,
        }


class ServiceTool:
    def __init__(self, backend: ServiceBackend) -> None:
        self.backend = backend
        self._descriptor = ToolDescriptor(
            id="runtime.service",
            description="Controlled service inspection and lifecycle operations",
            capabilities=(
                ToolCapability("service_status", SafetyClass.READ_ONLY),
                ToolCapability("list_services", SafetyClass.READ_ONLY),
                ToolCapability("service_start", SafetyClass.MUTATING),
                ToolCapability("service_stop", SafetyClass.MUTATING),
                ToolCapability("service_restart", SafetyClass.MUTATING),
            ),
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        try:
            if operation.name == "service_status":
                return OperationResult.ok(operation.id, self._as_dict(self.backend.get_status(operation.target.identifier)))
            if operation.name == "list_services":
                return OperationResult.ok(
                    operation.id,
                    {"services": [self._as_dict(s) for s in self.backend.list_services()]},
                )
            actions = {
                "service_start": self.backend.start,
                "service_stop": self.backend.stop,
                "service_restart": self.backend.restart,
            }
            action = actions.get(operation.name)
            if action is None:
                return OperationResult.fail(
                    operation.id,
                    OperationError(ErrorCategory.UNSUPPORTED_OPERATION, f"Unsupported service operation: {operation.name!r}"),
                )
            return OperationResult.ok(operation.id, self._as_dict(action(operation.target.identifier)))
        except ServiceNotFoundError as exc:
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.VALIDATION_ERROR, str(exc)))
        except TimeoutError as exc:
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.TIMEOUT, str(exc) or "service action timed out"))
        except PermissionError as exc:
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.PERMISSION_DENIED, str(exc)))
        except Exception as exc:  # noqa: BLE001
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.EXECUTION_FAILURE, str(exc)))

    @staticmethod
    def _as_dict(service: Any) -> dict[str, Any]:
        return {
            "name": service.name,
            "state": service.state.value,
            "pid": service.pid,
            "desired_state": service.desired_state.value,
            "health_state": service.health_state,
            "message": service.message,
            "extra": dict(service.extra),
        }


class HealthTool:
    def __init__(self, inspector: ProcessInspector | None = None, service_backend: ServiceBackend | None = None) -> None:
        self.inspector = inspector or LocalProcessInspector()
        self.service_backend = service_backend
        self._descriptor = ToolDescriptor(
            id="runtime.health",
            description="Structured process and service health checks",
            capabilities=(ToolCapability("health_check", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        started = time.monotonic()
        target = operation.target
        try:
            if target.kind == "self":
                result = HealthCheckResult(target="self:runtime", status=HealthStatus.HEALTHY, diagnostic={"pid": os.getpid()})
            elif target.kind == "process":
                pid = int(operation.parameters.get("pid", target.identifier))
                alive = self.inspector.is_alive(pid)
                result = HealthCheckResult(
                    target=f"process:{pid}",
                    status=HealthStatus.HEALTHY if alive else HealthStatus.UNHEALTHY,
                    diagnostic={"pid": pid, "alive": alive},
                    failure_reason=None if alive else "process_not_alive",
                )
            elif target.kind == "service" and self.service_backend is not None:
                service = self.service_backend.get_status(target.identifier)
                healthy = service.health_state == "ok"
                result = HealthCheckResult(
                    target=f"service:{target.identifier}",
                    status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
                    diagnostic={"state": service.state.value, "pid": service.pid},
                    failure_reason=None if healthy else service.message or "service_unhealthy",
                )
            else:
                result = HealthCheckResult(
                    target=f"{target.kind}:{target.identifier}",
                    status=HealthStatus.UNKNOWN,
                    failure_reason="unsupported_health_target",
                )
            data = result.to_dict()
            data["latency_ms"] = (time.monotonic() - started) * 1000
            return OperationResult.ok(operation.id, data)
        except (ValueError, InvalidPIDError):
            return OperationResult.ok(
                operation.id,
                HealthCheckResult(
                    target=f"{target.kind}:{target.identifier}",
                    status=HealthStatus.UNHEALTHY,
                    failure_reason="invalid_process_identifier",
                ).to_dict(),
            )
        except ServiceNotFoundError:
            return OperationResult.ok(
                operation.id,
                HealthCheckResult(
                    target=f"service:{target.identifier}",
                    status=HealthStatus.UNHEALTHY,
                    failure_reason="service_not_found",
                ).to_dict(),
            )


class DiagnosticsTool:
    def __init__(
        self,
        registry: ToolRegistry,
        service_backend: ServiceBackend | None = None,
        config: OperationsConfig | None = None,
        inspector: ProcessInspector | None = None,
    ) -> None:
        self.registry = registry
        self.service_backend = service_backend
        self.config = config or OperationsConfig()
        self.inspector = inspector or LocalProcessInspector()
        self._descriptor = ToolDescriptor(
            id="runtime.diagnostics",
            description="Safe runtime diagnostics without environment or secret dumps",
            capabilities=(ToolCapability("diagnostics", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        process = self.inspector.get_process(os.getpid())
        services = ()
        if self.service_backend is not None:
            services = tuple(
                {
                    "name": service.name,
                    "state": service.state.value,
                    "health_state": service.health_state,
                }
                for service in self.service_backend.list_services()
            )
        snapshot = DiagnosticsSnapshot(
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            os_name=os.name,
            process={"pid": process.pid, "name": process.name, "status": process.status},
            registered_tools=tuple(d.id for d in self.registry.list_tools()),
            configuration={
                "execution_timeout_seconds": self.config.execution_timeout_seconds,
                "log_level": self.config.log_level,
            },
            services=services,
        )
        return OperationResult.ok(operation.id, snapshot.to_dict())


def register_runtime_tools(
    registry: ToolRegistry,
    *,
    inspector: ProcessInspector | None = None,
    service_backend: ServiceBackend | None = None,
    config: OperationsConfig | None = None,
) -> None:
    """Register all standard runtime tools into a caller-owned registry."""
    inspector = inspector or LocalProcessInspector()
    service_backend = service_backend or LocalServiceBackend(inspector)
    registry.register(ProcessTool(inspector))
    registry.register(ServiceTool(service_backend))
    registry.register(HealthTool(inspector, service_backend))
    registry.register(DiagnosticsTool(registry, service_backend, config or OperationsConfig(), inspector))
