"""Versioned, transport-neutral contracts for Yasin ecosystem adapters."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationResult
from yasin_operations.safety.classification import SafetyClass

ADAPTER_CONTRACT_VERSION = "1.0"
_VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
_ALLOWED_STATES = frozenset({"unknown", "running", "stopped", "degraded", "unavailable", "failed"})
_MAX_SERVICE_NAME = 128
_MAX_VERSION = 64
_MAX_CAPABILITIES = 128


@dataclass(frozen=True)
class ServiceSnapshot:
    """Validated transport-neutral observation of an ecosystem service."""

    service: str
    available: bool
    state: str = "unknown"
    version: str | None = None
    capabilities: tuple[str, ...] = ()
    diagnostic: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    contract_version: str = ADAPTER_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.service, str) or not self.service.strip() or len(self.service) > _MAX_SERVICE_NAME:
            raise ValueError("invalid service identity")
        if not isinstance(self.available, bool):
            raise ValueError("available must be a boolean")
        if self.state not in _ALLOWED_STATES:
            raise ValueError(f"unsupported service state: {self.state!r}")
        if self.version is not None and (
            not isinstance(self.version, str) or len(self.version) > _MAX_VERSION or not _VERSION_RE.fullmatch(self.version)
        ):
            raise ValueError("invalid service version")
        if not isinstance(self.contract_version, str) or not _VERSION_RE.fullmatch(self.contract_version):
            raise ValueError("invalid adapter contract version")
        capabilities = tuple(self.capabilities)
        if len(capabilities) > _MAX_CAPABILITIES:
            raise ValueError("too many service capabilities")
        if any(not isinstance(item, str) or not item.strip() for item in capabilities):
            raise ValueError("service capabilities must be non-empty strings")
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("service capabilities must be unique")
        if tuple(sorted(capabilities)) != capabilities:
            raise ValueError("service capabilities must be deterministically ordered")
        if not isinstance(self.diagnostic, Mapping):
            raise ValueError("diagnostic must be a mapping")

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

    @classmethod
    def from_operation(cls, result: OperationResult) -> "AdapterResult":
        error = None
        if result.error is not None:
            error = {"category": result.error.category.value, "message": result.error.message,
                     "details": dict(result.error.details)}
        return cls(result.success, dict(result.data or {}), error)


class EcosystemServiceAdapter:
    """Common implementation for optional Yasin-AI/Press/Relay adapters."""

    service_name: str = ""
    operation_prefix: str = ""

    def __init__(self, probe: ServiceProbe, executor: Executor | None = None) -> None:
        if not self.service_name or not self.operation_prefix:
            raise ValueError("service_name and operation_prefix must be defined")
        self.probe = probe
        self.executor = executor

    @property
    def contract_version(self) -> str:
        return ADAPTER_CONTRACT_VERSION

    @property
    def supported_operations(self) -> tuple[str, ...]:
        return tuple(sorted(f"{self.operation_prefix}_{suffix}"
                            for suffix in ("status", "health", "version", "capabilities")))

    def inspect(self) -> ServiceSnapshot:
        try:
            snapshot = self.probe.inspect(self.service_name)
            if not isinstance(snapshot, ServiceSnapshot):
                raise TypeError("probe returned an invalid ServiceSnapshot")
            if snapshot.service != self.service_name:
                return ServiceSnapshot(service=self.service_name, available=False, state="failed",
                                       error="probe returned a mismatched service identity")
            if snapshot.contract_version != self.contract_version:
                return ServiceSnapshot(service=self.service_name, available=False, state="failed",
                                       error="unsupported adapter contract version")
            return snapshot
        except (ConnectionError, TimeoutError, OSError):
            return ServiceSnapshot(service=self.service_name, available=False, state="unavailable",
                                   error="service probe unavailable")
        except (ValueError, TypeError):
            return ServiceSnapshot(service=self.service_name, available=False, state="failed",
                                   error="service probe returned invalid data")
        except Exception:  # noqa: BLE001 - adapter boundary must remain isolated
            return ServiceSnapshot(service=self.service_name, available=False, state="failed",
                                   error="service probe failed")

    def build_operation(self, operation_name: str, *, target_identifier: str = "service",
                        parameters: Mapping[str, Any] | None = None) -> Operation:
        if operation_name not in self.supported_operations:
            raise ValueError(f"unsupported capability: {operation_name!r}")
        if not isinstance(target_identifier, str) or not target_identifier.strip():
            raise ValueError("target_identifier must be a non-empty string")
        if parameters is not None and not isinstance(parameters, Mapping):
            raise ValueError("parameters must be a mapping")
        return Operation(name=operation_name, target=OperationTarget(kind="ecosystem_service", identifier=target_identifier),
                         safety_class=SafetyClass.READ_ONLY, parameters=dict(parameters or {}))

    def execute(self, operation_name: str, *, target_identifier: str = "service",
                parameters: Mapping[str, Any] | None = None) -> AdapterResult:
        try:
            operation = self.build_operation(operation_name, target_identifier=target_identifier, parameters=parameters)
        except ValueError as exc:
            return AdapterResult(False, error={"category": ErrorCategory.VALIDATION_ERROR.value,
                                                "message": str(exc), "details": {}})
        if self.executor is None:
            return AdapterResult(False, error={"category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value,
                                                "message": "Yasin-Operations executor is unavailable", "details": {}})
        try:
            return AdapterResult.from_operation(self.executor.execute(operation))
        except (ConnectionError, TimeoutError) as exc:
            return AdapterResult(False, error={"category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value,
                                                "message": str(exc) or "executor unavailable", "details": {}})
        except Exception:
            return AdapterResult(False, error={"category": ErrorCategory.INTERNAL_ERROR.value,
                                                "message": "ecosystem operation failed", "details": {}})

    def inspect_result(self) -> AdapterResult:
        snapshot = self.inspect()
        if not snapshot.available:
            validation_errors = {"service probe returned invalid data", "unsupported adapter contract version",
                                 "probe returned a mismatched service identity"}
            category = (ErrorCategory.VALIDATION_ERROR.value if snapshot.error in validation_errors
                        else ErrorCategory.UNAVAILABLE_DEPENDENCY.value)
            return AdapterResult(False, data=snapshot.as_dict(), error={"category": category,
                                                                         "message": snapshot.error or "service unavailable",
                                                                         "details": {}})
        return AdapterResult(True, data=snapshot.as_dict())
