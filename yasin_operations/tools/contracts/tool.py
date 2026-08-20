"""Tool capability and execution contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from yasin_operations.core.operations.models import Operation
from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass


@dataclass(frozen=True)
class ToolCapability:
    """One operation capability plus explicit retry/idempotency semantics.

    `retryable` means the tool can safely be invoked again after a retryable
    failure. For mutating operations, `idempotent` is additionally required;
    the executor never assumes mutation idempotency from the operation name.
    """

    operation_name: str
    safety_class: SafetyClass
    retryable: bool = False
    idempotent: bool = False

    def __post_init__(self) -> None:
        if not self.operation_name or not self.operation_name.strip():
            raise ValueError("ToolCapability.operation_name must not be empty")
        if not isinstance(self.safety_class, SafetyClass):
            raise ValueError("ToolCapability.safety_class must be a SafetyClass member")
        if not isinstance(self.retryable, bool) or not isinstance(self.idempotent, bool):
            raise ValueError("retryable and idempotent must be booleans")
        if self.idempotent and not self.retryable:
            raise ValueError("idempotent capability must also be retryable")


@dataclass(frozen=True)
class ToolDescriptor:
    id: str
    description: str
    capabilities: tuple[ToolCapability, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("ToolDescriptor.id must not be empty")
        if not self.description or not self.description.strip():
            raise ValueError("ToolDescriptor.description must not be empty")

    def supports(self, operation_name: str) -> bool:
        return any(c.operation_name == operation_name for c in self.capabilities)

    def capability_for(self, operation_name: str) -> ToolCapability | None:
        for c in self.capabilities:
            if c.operation_name == operation_name:
                return c
        return None


@runtime_checkable
class Tool(Protocol):
    @property
    def descriptor(self) -> ToolDescriptor:
        ...

    def execute(self, operation: Operation) -> OperationResult:
        ...
