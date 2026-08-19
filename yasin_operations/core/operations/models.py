"""Typed contracts for operations.

These are pure data models: no execution logic, no I/O, no
dependency on any specific tool, shell, or external service. This
keeps the Core importable and testable in complete isolation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional

from yasin_operations.safety.classification import SafetyClass


class OperationStatus(str, Enum):
    """Explicit, deterministic lifecycle for an operation.

    Legal transitions:
        PENDING -> RUNNING -> SUCCEEDED
        PENDING -> RUNNING -> FAILED
        PENDING -> CANCELLED
        RUNNING -> CANCELLED
        PENDING -> DENIED

    Terminal states: SUCCEEDED, FAILED, CANCELLED, DENIED.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"


_TERMINAL_STATUSES = frozenset(
    {
        OperationStatus.SUCCEEDED,
        OperationStatus.FAILED,
        OperationStatus.CANCELLED,
        OperationStatus.DENIED,
    }
)

_LEGAL_TRANSITIONS: dict[OperationStatus, frozenset[OperationStatus]] = {
    OperationStatus.PENDING: frozenset(
        {OperationStatus.RUNNING, OperationStatus.CANCELLED, OperationStatus.DENIED}
    ),
    OperationStatus.RUNNING: frozenset(
        {
            OperationStatus.SUCCEEDED,
            OperationStatus.FAILED,
            OperationStatus.CANCELLED,
        }
    ),
    OperationStatus.SUCCEEDED: frozenset(),
    OperationStatus.FAILED: frozenset(),
    OperationStatus.CANCELLED: frozenset(),
    OperationStatus.DENIED: frozenset(),
}


def is_terminal(status: OperationStatus) -> bool:
    return status in _TERMINAL_STATUSES


def is_legal_transition(
    current: OperationStatus, target: OperationStatus
) -> bool:
    return target in _LEGAL_TRANSITIONS[current]


class InvalidTransitionError(Exception):
    """Raised when an illegal lifecycle transition is attempted."""

    def __init__(self, current: OperationStatus, target: OperationStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal operation status transition: {current.value} -> {target.value}"
        )


@dataclass(frozen=True)
class OperationTarget:
    """What an operation acts on.

    kind is a free-form category (e.g. "service", "file", "tool")
    interpreted by the tool/adapter that ultimately executes the
    operation. The Core does not interpret kind/identifier itself.
    """

    kind: str
    identifier: str


@dataclass(frozen=True)
class OperationMetadata:
    """Free-form, non-authoritative metadata attached to an operation.

    Must not be used to carry information the Core relies on for
    correctness (e.g. safety classification) -- that belongs in
    typed fields, not here.
    """

    values: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Operation:
    """A single, immutable description of an operation to perform.

    id is generated automatically if not supplied. name identifies
    what kind of operation this is (interpreted by the tool
    registry / execution layer). parameters are the operation's
    typed-by-convention input; validation of parameter contents is
    the responsibility of the Tool that declares support for `name`
    (see tools/contracts.py), not of this dataclass.
    """

    name: str
    target: OperationTarget
    safety_class: SafetyClass
    parameters: Mapping[str, Any] = field(default_factory=dict)
    metadata: OperationMetadata = field(default_factory=OperationMetadata)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Operation.name must not be empty")
        if not isinstance(self.safety_class, SafetyClass):
            raise ValueError(
                "Operation.safety_class must be a SafetyClass member"
            )


@dataclass(frozen=True)
class OperationState:
    """The current lifecycle state of an operation.

    Separate from Operation itself so the immutable operation
    description and its mutable-over-time status are not conflated.
    Transitions must go through OperationState.transition_to(), which
    enforces is_legal_transition() and raises InvalidTransitionError
    on an illegal move.
    """

    operation_id: str
    status: OperationStatus = OperationStatus.PENDING
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def transition_to(self, target: OperationStatus) -> "OperationState":
        if not is_legal_transition(self.status, target):
            raise InvalidTransitionError(self.status, target)
        return OperationState(
            operation_id=self.operation_id,
            status=target,
            updated_at=datetime.now(timezone.utc),
        )
