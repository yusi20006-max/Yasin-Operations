"""Structured, machine-readable results and errors for operations.

Deliberately avoids making arbitrary strings the primary API: error
category is a typed enum, and callers should branch on category
rather than parsing message text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class ErrorCategory(str, Enum):
    """Extensible, intentionally minimal error taxonomy.

    Kept small on purpose (per Issue #1 scope: "do not
    over-engineer the taxonomy, keep it extensible"). New categories
    can be added as real needs arise in later issues.
    """

    VALIDATION_ERROR = "validation_error"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    EXECUTION_FAILURE = "execution_failure"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    UNAVAILABLE_DEPENDENCY = "unavailable_dependency"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class OperationError:
    """A structured error produced by attempting an operation."""

    category: ErrorCategory
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.category, ErrorCategory):
            raise ValueError("OperationError.category must be an ErrorCategory member")
        if not self.message or not self.message.strip():
            raise ValueError("OperationError.message must not be empty")


@dataclass(frozen=True)
class OperationResult:
    """The outcome of attempting to execute an operation.

    Exactly one of `error` and `data` is expected to be meaningful:
    a successful result carries `data` and no `error`; a failed
    result carries `error` and typically no `data`. This is a
    convention enforced by callers (e.g. the execution layer), not
    by this dataclass, to keep the model simple.
    """

    operation_id: str
    success: bool
    data: Optional[Mapping[str, Any]] = None
    error: Optional[OperationError] = None
    completed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.success and self.error is not None:
            raise ValueError(
                "OperationResult.error must be None when success is True"
            )
        if not self.success and self.error is None:
            raise ValueError(
                "OperationResult.error must be set when success is False"
            )

    @classmethod
    def ok(
        cls, operation_id: str, data: Optional[Mapping[str, Any]] = None
    ) -> "OperationResult":
        return cls(operation_id=operation_id, success=True, data=data or {})

    @classmethod
    def fail(cls, operation_id: str, error: OperationError) -> "OperationResult":
        return cls(operation_id=operation_id, success=False, error=error)
