"""Canonical contracts for optional Yasin ecosystem service adapters."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationResult
from yasin_operations.safety.classification import SafetyClass

CONTRACT_VERSION = 1
VALID_SERVICE_STATES = frozenset({"unknown", "running", "stopped", "starting", "stopping", "degraded", "failed", "unavailable"})
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]{0,63}$")


@dataclass(frozen=True)
class ServiceSnapshot:
    """Validated, transport-neutral observed state of an ecosystem service."""

    service: str
    available: bool
    state: str = "unknown"
    version: str | None = None
    capabilities: tuple[str, ...] = ()
    diagnostic: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.service, str) or not self.service.strip():
            raise ValueError("snapshot service must be a non-empty string")
        if not isinstance(self.available, bool):
            raise ValueError("snapshot available must be a boolean")
        if self.state not in VALID_SERVICE_STATES:
            raise ValueError(f"unsupported service state: {self.state!r}")
        if self.version is not None and (not isinstance(self.version, str) or not _VERSION_RE.fullmatch(self.version)):
            raise ValueError("snapshot version has an invalid format")
        if not isinstance(self.capabilities, tuple):
            raise ValueError("snapshot capabilities must be a tuple")
        normalized = tuple(sorted(self.capabilities))
        if any(not isinstance(item, str) or not item.strip() for item in normalized):
            raise ValueError("snapshot capabilities must contain non-empty strings")
        if len(set(normalized)) != len(normalized):
            raise ValueError("snapshot capabilities must be unique")
        if normalized != self.capabilities:
            raise ValueError("snapshot capabilities must be deterministically sorted")
        if not isinstance(self.diagnostic, Mapping):
            raise ValueError("snapshot diagnostic must be a mapping")
        if self.error is not None and not isinstance(self.error, str):
            raise ValueError("snapshot error must be a string when provided")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(f"unsupported adapter contract version: {self.contract_version!r}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "service": self.service,
            "available": self.available,
            "state": self.state,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "diagnostic": dict(self.diagnostic),
            "error": self.error,
        }


class ServiceProbe(Protocol):
    def inspect(self, service_name: str) -> ServiceSnapshot:
        ...


@dataclass(frozen=True)
class AdapterResult:
    success: bool
    data: Mapping[str, Any] = field(default_factory=dict)
    error: Mapping[str, Any] | None = None
    contract_version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported adapter result contract version")
        if self.success and self.error is not None:
            raise ValueError("successful adapter result cannot contain an error")
        if not self.success and self.error is None:
            raise ValueError("failed adapter result must contain an error")

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
    """Thin provider-neutral adapter shared by the optional ecosystem services."""

    service_name: str = ""
    operation_prefix: str = ""

    def __init__(self, probe: ServiceProbe, executor: Executor | None = None) -> None:
        if not self.service_name or not self.operation_prefix:
            raise ValueError("service_name and operation_prefix must be defined")
        self.probe = probe
        self.executor = executor

    @property
    def contract_version(self) -> int:
        return CONTRACT_VERSION

    @property
    def supported_operations(self) -> tuple[str, ...]:
        return tuple(f"{self.operation_prefix}_{suffix}" for suffix in ("status", "health", "version", "capabilities"))

    def inspect(self) -> ServiceSnapshot:
        try:
            snapshot = self.probe.inspect(self.service_name)
            if not isinstance(snapshot, ServiceSnapshot):
                raise TypeError("probe must return ServiceSnapshot")
            if snapshot.service != self.service_name:
                return ServiceSnapshot(service=self.service_name, available=False, state="unavailable", error="probe returned a mismatched service identity")
            return snapshot
        except TimeoutError as exc:
            return ServiceSnapshot(service=self.service_name, available=False, state="unavailable", error=str(exc) or "service probe timed out")
        except (ConnectionError, OSError) as exc:
            return ServiceSnapshot(service=self.service_name, available=False, state="unavailable", error=str(exc) or "service probe unavailable")
        except Exception as exc:  # noqa: BLE001
            return ServiceSnapshot(service=self.service_name, available=False, state="failed", error=str(exc) or "service probe failed")

    def build_operation(self, operation_name: str, *, target_identifier: str = "service", parameters: Mapping[str, Any] | None = None) -> Operation:
        if operation_name not in self.supported_operations:
            raise ValueError(f"unsupported capability: {operation_name!r}")
        return Operation(name=operation_name, target=OperationTarget(kind="ecosystem_service", identifier=target_identifier), safety_class=SafetyClass.READ_ONLY, parameters=dict(parameters or {}))

    def execute(self, operation_name: str, *, target_identifier: str = "service", parameters: Mapping[str, Any] | None = None) -> AdapterResult:
        try:
            operation = self.build_operation(operation_name, target_identifier=target_identifier, parameters=parameters)
        except (TypeError, ValueError) as exc:
            return AdapterResult(False, error={"category": ErrorCategory.VALIDATION_ERROR.value, "message": str(exc), "details": {}})
        if self.executor is None:
            return AdapterResult(False, error={"category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value, "message": "Yasin-Operations executor is unavailable", "details": {}})
        try:
            return AdapterResult.from_operation(self.executor.execute(operation, actor="ecosystem-adapter", source=f"adapter.{self.service_name}"))
        except TimeoutError as exc:
            return AdapterResult(False, error={"category": ErrorCategory.TIMEOUT.value, "message": str(exc) or "adapter execution timed out", "details": {}})
        except (ConnectionError, OSError) as exc:
            return AdapterResult(False, error={"category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value, "message": str(exc) or "adapter dependency unavailable", "details": {}})
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(False, error={"category": ErrorCategory.INTERNAL_ERROR.value, "message": str(exc), "details": {}})

    def inspect_result(self) -> AdapterResult:
        snapshot = self.inspect()
        data = snapshot.as_dict()
        if not snapshot.available:
            return AdapterResult(False, data=data, error={"category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value, "message": snapshot.error or "service unavailable", "details": {}})
        return AdapterResult(True, data=data)
