"""Diagnostics snapshot abstraction.

Produces structured runtime information without dumping secrets or
full environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class DiagnosticsSnapshot:
    """Structured diagnostic snapshot of the runtime environment."""

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    python_version: str = ""
    platform: str = ""
    os_name: str = ""
    process: Mapping[str, Any] = field(default_factory=dict)
    registered_tools: tuple[str, ...] = ()
    configuration: Mapping[str, Any] = field(default_factory=dict)
    services: tuple[Mapping[str, Any], ...] = ()
    extra: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "python_version": self.python_version,
            "platform": self.platform,
            "os_name": self.os_name,
            "process": dict(self.process),
            "registered_tools": list(self.registered_tools),
            "configuration": dict(self.configuration),
            "services": [dict(s) for s in self.services],
            "extra": dict(self.extra),
        }
