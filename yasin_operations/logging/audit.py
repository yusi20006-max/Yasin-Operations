"""Structured operational logging interfaces.

Lightweight by design for this issue: defines the audit record shape
and a minimal recorder Protocol so callers can supply their own sink
(stdout, file, remote log service) in later issues. A complete
security/audit implementation is explicitly Issue #4's scope, not
this one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol

from yasin_operations.core.operations.models import OperationStatus, OperationTarget
from yasin_operations.core.results.models import OperationError


@dataclass(frozen=True)
class AuditRecord:
    """A single structured audit log entry for an operation.

    Carries exactly the fields Issue #1 specifies: operation ID,
    timestamp, operation name, target, status, result/error, and
    metadata.
    """

    operation_id: str
    operation_name: str
    target: OperationTarget
    status: OperationStatus
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    error: Optional[OperationError] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class AuditRecorder(Protocol):
    """A sink for AuditRecord entries.

    In this issue, only a minimal in-memory implementation
    (InMemoryAuditRecorder below) exists, useful for tests and as a
    reference implementation. Real sinks (file, remote) are later
    issue scope.
    """

    def record(self, entry: AuditRecord) -> None:
        ...


class InMemoryAuditRecorder:
    """Reference AuditRecorder that keeps entries in a list.

    Intended for tests and as a minimal working implementation, not
    as a production audit sink.
    """

    def __init__(self) -> None:
        self.entries: list[AuditRecord] = []

    def record(self, entry: AuditRecord) -> None:
        self.entries.append(entry)
