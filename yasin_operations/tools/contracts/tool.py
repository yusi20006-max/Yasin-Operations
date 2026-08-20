"""Tool contract.

A Tool declares what operation names it supports and how to execute
them, without the Core needing to know its implementation details
(shell, HTTP call, in-process Python, etc). Concrete tools live in
adapters/ in later issues; this module only defines the contract
they must satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from yasin_operations.core.operations.models import Operation
from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass


@dataclass(frozen=True)
class ToolCapability:
    """One operation name a tool supports, and its execution semantics.

    ``retryable`` means a failed attempt is safe to invoke again. For a
    mutating operation, ``idempotent`` must also be true before the Executor
    will retry it. Both flags default to false so existing tools fail closed.
    """

    operation_name: str
    safety_class: SafetyClass
    retryable: bool = False
    idempotent: bool = False


@dataclass(frozen=True)
class ToolDescriptor:
    """Static identity/description metadata for a tool.

    Kept separate from the executable Tool protocol below so a
    registry can list/describe tools without needing a live
    instance of every tool.
    """

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
    """Protocol a concrete tool implementation must satisfy.

    Using a Protocol (structural typing) rather than an ABC keeps
    the Core decoupled from any specific tool base class; adapters
    in later issues can implement this without importing a Core
    base class.
    """

    @property
    def descriptor(self) -> ToolDescriptor:
        """Static identity/description/capability metadata."""
        ...

    def execute(self, operation: Operation) -> OperationResult:
        """Execute the given operation and return a structured result.

        Implementations must not raise for expected failure modes;
        they should return OperationResult.fail(...) with an
        appropriate OperationError instead. Unexpected exceptions
        are the execution layer's responsibility to catch and wrap.
        """
        ...
