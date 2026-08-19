"""Service abstraction.

Represents a named service without hard-coding any specific product
(YasinPress, YasinRelay, Hermes, Yasin-AI, systemd units, etc.).
Lifecycle mutations are typed and must go through an adapter that
only runs predefined, validated actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Protocol, runtime_checkable


class ServiceState(str, Enum):
    """Observed or desired service state."""

    UNKNOWN = "unknown"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    DEGRADED = "degraded"


class ServiceNotFoundError(Exception):
    """Raised when a requested service name is not registered/known."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Service not found: {name!r}")


@dataclass(frozen=True)
class ServiceInfo:
    """Structured description of a service."""

    name: str
    state: ServiceState
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    desired_state: ServiceState = ServiceState.UNKNOWN
    health_state: str = "unknown"
    message: Optional[str] = None
    extra: Mapping[str, object] = field(default_factory=dict)


@runtime_checkable
class ServiceBackend(Protocol):
    """Backend contract for service inspection and lifecycle.

    START/STOP/RESTART are mutating; STATUS is read-only.
    Implementations must not accept arbitrary user-supplied command
    strings — only predefined actions associated with registered
    service definitions.
    """

    def list_services(self) -> list[ServiceInfo]:
        ...

    def get_status(self, name: str) -> ServiceInfo:
        """Return current status, or raise ServiceNotFoundError."""
        ...

    def start(self, name: str) -> ServiceInfo:
        """Attempt to start the service. Returns resulting ServiceInfo.
        Raises ServiceNotFoundError if unknown."""
        ...

    def stop(self, name: str) -> ServiceInfo:
        """Attempt to stop the service."""
        ...

    def restart(self, name: str) -> ServiceInfo:
        """Attempt to restart the service."""
        ...
