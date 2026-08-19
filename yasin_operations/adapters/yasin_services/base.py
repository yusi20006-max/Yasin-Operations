"""Transport-neutral optional adapters for Yasin services."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Optional, Protocol

from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.safety.classification import SafetyClass


class EcosystemStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class EcosystemService:
    id: str
    name: str
    version: Optional[str]
    status: EcosystemStatus
    capabilities: tuple[str, ...] = ()
    details: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterRequest:
    operation: str
    target: OperationTarget
    parameters: Mapping[str, object] = field(default_factory=dict)
    safety_class: SafetyClass = SafetyClass.READ_ONLY
    metadata: Mapping[str, object] = field(default_factory=dict)


class Probe(Protocol):
    def __call__(self) -> EcosystemService: ...


class EcosystemAdapter:
    """Optional adapter with no dependency on target project packages."""

    def __init__(self, service_id: str, name: str, probe: Probe, supported: Mapping[str, SafetyClass]):
        self.service_id = service_id
        self.name = name
        self._probe = probe
        self._supported = dict(supported)

    def inspect(self) -> EcosystemService:
        try:
            return self._probe()
        except Exception as exc:
            return EcosystemService(self.service_id, self.name, None, EcosystemStatus.UNAVAILABLE, (), {"error": str(exc)})

    def capabilities(self) -> Mapping[str, SafetyClass]:
        return dict(self._supported)

    def build_operation(self, request: AdapterRequest) -> Operation | OperationResult:
        expected = self._supported.get(request.operation)
        if expected is None:
            return OperationResult.fail(
                request.metadata.get("operation_id", "adapter-request"),
                OperationError(ErrorCategory.UNSUPPORTED_OPERATION, f"Unsupported capability: {request.operation!r}", {"adapter": self.service_id}),
            )
        if expected != request.safety_class:
            return OperationResult.fail(
                request.metadata.get("operation_id", "adapter-request"),
                OperationError(ErrorCategory.VALIDATION_ERROR, "Safety class does not match adapter capability", {"expected": expected.value, "received": request.safety_class.value}),
            )
        return Operation(
            name=request.operation,
            target=request.target,
            safety_class=request.safety_class,
            parameters=dict(request.parameters),
        )

    def translate_result(self, operation: Operation, result: OperationResult) -> OperationResult:
        return result
