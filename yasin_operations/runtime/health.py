"""Structured health-check abstraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class HealthCheckResult:
    """Machine-readable outcome of a single health check."""

    target: str
    status: HealthStatus
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    latency_ms: Optional[float] = None
    diagnostic: Mapping[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "diagnostic": dict(self.diagnostic),
            "failure_reason": self.failure_reason,
        }
