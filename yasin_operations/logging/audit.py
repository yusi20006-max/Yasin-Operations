"""Structured operational audit trail.

Audit records are immutable and safe to pass between adapters. The reference
recorder is thread-safe and keeps an in-memory history for local operation and
test use; persistent sinks remain replaceable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Mapping, Optional, Protocol

from yasin_operations.core.operations.models import OperationStatus, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError

_MAX_AUDIT_TEXT = 2048
_SENSITIVE_KEY_RE = re.compile(
    r"(?:password|passwd|token|secret|api[_-]?key|authorization|cookie|credential|private[_-]?key)",
    re.IGNORECASE,
)
_SENSITIVE_TEXT_RE = re.compile(
    r"(?i)(password|passwd|token|secret|api[_-]?key|authorization|cookie|credential|private[_-]?key)\s*[:=]\s*[^\s,;]+"
)


def _sanitize_text(value: str) -> str:
    redacted = _SENSITIVE_TEXT_RE.sub(lambda match: f"{match.group(1)}=<redacted>", value)
    if len(redacted) > _MAX_AUDIT_TEXT:
        return redacted[:_MAX_AUDIT_TEXT] + "…"
    return redacted


def sanitize_audit_value(value: Any, *, _depth: int = 0) -> Any:
    """Return a bounded, credential-safe representation suitable for audit."""
    if _depth > 6:
        return "<max-depth>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = _sanitize_text(str(key))
            if _SENSITIVE_KEY_RE.search(key_text):
                result[key_text] = "<redacted>"
            else:
                result[key_text] = sanitize_audit_value(item, _depth=_depth + 1)
        return result
    if isinstance(value, (list, tuple, set, frozenset)):
        return [sanitize_audit_value(item, _depth=_depth + 1) for item in value]
    return f"<omitted:{type(value).__name__}>"


def _sanitize_error(error: Optional[OperationError]) -> Optional[OperationError]:
    if error is None:
        return None
    return OperationError(
        category=error.category,
        message=_sanitize_text(error.message),
        details=sanitize_audit_value(error.details),
    )


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
        if not isinstance(self.operation_id, str) or not self.operation_id.strip():
            raise ValueError("AuditRecord.operation_id must not be empty")
        if not isinstance(self.operation_name, str) or not self.operation_name.strip():
            raise ValueError("AuditRecord.operation_name must not be empty")
        if not isinstance(self.actor, str) or not self.actor.strip():
            raise ValueError("AuditRecord.actor must not be empty")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("AuditRecord.source must not be empty")
        if self.correlation_id is not None and (not isinstance(self.correlation_id, str) or not self.correlation_id.strip()):
            raise ValueError("AuditRecord.correlation_id must be a non-empty string when provided")
        if not isinstance(self.status, OperationStatus):
            raise ValueError("AuditRecord.status must be an OperationStatus member")
        if not isinstance(self.dry_run, bool):
            raise ValueError("AuditRecord.dry_run must be a boolean")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("AuditRecord.duration_ms must not be negative")
        object.__setattr__(self, "metadata", sanitize_audit_value(self.metadata))
        object.__setattr__(self, "error", _sanitize_error(self.error))


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
