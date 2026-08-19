"""Common contracts for optional Yasin ecosystem service adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.safety.classification import SafetyClass


@dataclass(frozen=True)
class ServiceSnapshot:
    """Transport-neutral observed state of an ecosystem service."""

    service: str
    available: bool
    state: str = "unknown"
    version: str | None = None
    capabilities: tuple[str, ...] = ()
    diagnostic: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "service": self.service,
            "available": self.available,
            "state": self.state,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "diagnostic": dict(self.diagnostic),
            "error": self.error,
        }


class ServiceProbe(Protocol):
    """External transport supplied by the embedding application."""

    def inspect(self, service_name: str) -> ServiceSnapshot:
        ...


@dataclass(frozen=True)
class AdapterResult:
    """Structured adapter response independent of transport."""

    success: bool
    data: Mapping[str, Any] = field(default_factory=dict)
    error: Mapping[str, Any] | None = None

    @classmethod
    def from_operation(cls, result: OperationResult) -> "AdapterResult":
        error = None
        if result.error is not None:
            error = {
                "category": result.error.category.value,
                "message": result.error.message,
                "details": dict(result.error.details),
            }
        return cls(result.success, dict(result.data or {}), error)


class EcosystemServiceAdapter:
    """Base implementation shared by the three optional service adapters."""

    service_name: str = ""
    operation_prefix: str = ""

    def __init__(self, probe: ServiceProbe, executor: Executor | None = None) -> None:
        if not self.service_name or not self.operation_prefix:
            raise ValueError("service_name and operation_prefix must be defined")
        self.probe = probe
        self.executor = executor

    @property
    def supported_operations(self) -> tuple[str, ...]:
        return tuple(
            f"{self.operation_prefix}_{suffix}"
            for suffix in ("status", "health", "version", "capabilities")
        )

    def inspect(self) -> ServiceSnapshot:
        try:
            snapshot = self.probe.inspect(self.service_name)
            if snapshot.service != self.service_name:
                return ServiceSnapshot(
                    service=self.service_name,
                    available=False,
                    error="probe returned a mismatched service identity",
                )
            return snapshot
        except (ConnectionError, TimeoutError, OSError) as exc:
            return ServiceSnapshot(
                service=self.service_name,
                available=False,
                state="unavailable",
                error=str(exc) or "service probe unavailable",
            )
        except Exception as exc:  # noqa: BLE001 - adapter boundary stays structured
            return ServiceSnapshot(
                service=self.service_name,
                available=False,
                state="unavailable",
                error=str(exc),
            )

    def build_operation(
        self,
        operation_name: str,
        *,
        target_identifier: str = "service",
        parameters: Mapping[str, Any] | None = None,
    ) -> Operation:
        if operation_name not in self.supported_operations:
            raise ValueError(f"unsupported capability: {operation_name!r}")
        return Operation(
            name=operation_name,
            target=OperationTarget(kind="ecosystem_service", identifier=target_identifier),
            safety_class=SafetyClass.READ_ONLY,
            parameters=dict(parameters or {}),
        )

    def execute(
        self,
        operation_name: str,
        *,
        target_identifier: str = "service",
        parameters: Mapping[str, Any] | None = None,
    ) -> AdapterResult:
        operation = self.build_operation(
            operation_name,
            target_identifier=target_identifier,
            parameters=parameters,
        )
        if self.executor is None:
            return AdapterResult(
                success=False,
                error={
                    "category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value,
                    "message": "Yasin-Operations executor is unavailable",
                    "details": {},
                },
            )
        return AdapterResult.from_operation(self.executor.execute(operation))

    def inspect_result(self) -> AdapterResult:
        snapshot = self.inspect()
        if not snapshot.available:
            return AdapterResult(
                success=False,
                data=snapshot.as_dict(),
                error={
                    "category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value,
                    "message": snapshot.error or "service unavailable",
                    "details": {},
                },
            )
        return AdapterResult(success=True, data=snapshot.as_dict())
