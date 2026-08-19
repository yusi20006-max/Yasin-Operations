"""Generic Yasin service adapter implementation."""
from __future__ import annotations

from typing import Mapping, Optional

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.runtime.service import ServiceBackend, ServiceInfo, ServiceState
from yasin_operations.safety.classification import SafetyClass

from .base import AdapterRequest, EcosystemAdapter, EcosystemService, EcosystemStatus


class YasinServiceAdapter(EcosystemAdapter):
    def __init__(
        self,
        service_id: str,
        name: str,
        backend: Optional[ServiceBackend] = None,
        version: Optional[str] = None,
        capabilities: Optional[Mapping[str, SafetyClass]] = None,
    ) -> None:
        self.backend = backend
        self._version = version
        super().__init__(service_id, name, self._probe, capabilities or {"status": SafetyClass.READ_ONLY, "health": SafetyClass.READ_ONLY, "version": SafetyClass.READ_ONLY, "diagnostics": SafetyClass.READ_ONLY})

    def _probe(self) -> EcosystemService:
        if self.backend is None:
            return EcosystemService(self.service_id, self.name, self._version, EcosystemStatus.UNAVAILABLE, tuple(self.capabilities()))
        try:
            info = self.backend.get_status(self.service_id)
            status = EcosystemStatus.AVAILABLE if info.state == ServiceState.RUNNING else EcosystemStatus.DEGRADED
            return EcosystemService(self.service_id, self.name, self._version, status, tuple(self.capabilities()), {"service": _service_dict(info)})
        except Exception as exc:
            return EcosystemService(self.service_id, self.name, self._version, EcosystemStatus.UNAVAILABLE, tuple(self.capabilities()), {"error": str(exc)})

    def execute(self, request: AdapterRequest, executor: Executor) -> OperationResult:
        built = self.build_operation(request)
        if isinstance(built, OperationResult):
            return built
        return executor.execute(built)

    def status(self) -> OperationResult:
        if self.backend is None:
            return OperationResult.fail("adapter-status", OperationError(ErrorCategory.UNAVAILABLE_DEPENDENCY, "Service backend unavailable", {"adapter": self.service_id}))
        try:
            return OperationResult.ok("adapter-status", {"service": _service_dict(self.backend.get_status(self.service_id))})
        except Exception as exc:
            return OperationResult.fail("adapter-status", OperationError(ErrorCategory.EXECUTION_FAILURE, str(exc), {"adapter": self.service_id}))

    def health(self) -> OperationResult:
        status = self.status()
        if not status.success:
            return status
        service = status.data["service"]
        return OperationResult.ok("adapter-health", {"status": "healthy" if service["state"] == ServiceState.RUNNING.value else "degraded", "service": service})

    def diagnostics(self) -> OperationResult:
        inspected = self.inspect()
        return OperationResult.ok("adapter-diagnostics", {"id": inspected.id, "name": inspected.name, "version": inspected.version, "status": inspected.status.value, "capabilities": list(inspected.capabilities), "details": dict(inspected.details)})


def _service_dict(info: ServiceInfo) -> dict[str, object]:
    return {"name": info.name, "state": info.state.value, "pid": info.pid, "uptime_seconds": info.uptime_seconds, "desired_state": info.desired_state.value, "health_state": info.health_state, "message": info.message, "extra": dict(info.extra)}
