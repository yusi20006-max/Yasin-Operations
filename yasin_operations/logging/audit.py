"""Structured operational audit trail.

Audit records are immutable and safe to pass between adapters.  The
reference recorder is thread-safe and keeps an in-memory history for
local operation and test use; persistent sinks remain replaceable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Mapping, Optional, Protocol

from yasin_operations.core.operations.models import OperationStatus, OperationTarget
from yasin_operations.core.results.models import OperationError


@dataclass(frozen=True)
class AuditRecord:
    """A single auditable operation event."""

    operation_id: str
    operation_name: str
    target: OperationTarget
    status: OperationStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[OperationError] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    actor: str = "system"
    source: str = "unknown"
    correlation_id: Optional[str] = None
    duration_ms: Optional[float] = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise ValueError("AuditRecord.operation_id must not be empty")
        if not self.operation_name.strip():
            raise ValueError("AuditRecord.operation_name must not be empty")
        if not self.actor.strip():
            raise ValueError("AuditRecord.actor must not be empty")
        if not self.source.strip():
            raise ValueError("AuditRecord.source must not be empty")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("AuditRecord.duration_ms must not be negative")


class AuditRecorder(Protocol):
    """A replaceable sink for AuditRecord entries."""

    def record(self, entry: AuditRecord) -> None:
        ...


class InMemoryAuditRecorder:
    """Thread-safe reference recorder with query helpers."""

    def __init__(self) -> None:
        self._entries: list[AuditRecord] = []
        self._lock = Lock()

    @property
    def entries(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._entries)

    def record(self, entry: AuditRecord) -> None:
        with self._lock:
            self._entries.append(entry)

    def for_operation(self, operation_id: str) -> list[AuditRecord]:
        with self._lock:
            return [e for e in self._entries if e.operation_id == operation_id]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
