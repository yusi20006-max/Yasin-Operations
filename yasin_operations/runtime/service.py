"""Typed runtime service lifecycle contracts.

Service state is observed state. Lifecycle mutations are successful only when
the requested resulting state can be observed by the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Protocol, runtime_checkable


class ServiceState(str, Enum):
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


class ServiceCommandError(Exception):
    """Raised when a predefined lifecycle command fails or is not verified."""

    def __init__(self, name: str, action: str, returncode: int, message: str = ""):
        self.name = name
        self.action = action
        self.returncode = returncode
        self.message = message.strip()
        detail = self.message or f"exit code {returncode}"
        super().__init__(f"Service {action} failed for {name!r}: {detail}")


class ServiceTimeoutError(ServiceCommandError, TimeoutError):
    """Raised when a lifecycle command or readiness wait exceeds its budget."""

    def __init__(self, name: str, action: str, message: str = ""):
        super().__init__(name, action, -1, message or "lifecycle operation timed out")


class ServiceReadinessError(ServiceCommandError):
    """Raised when a control command succeeds but requested state is not observed."""

    def __init__(self, name: str, action: str, expected: ServiceState, observed: ServiceState):
        self.expected = expected
        self.observed = observed
        super().__init__(
            name,
            action,
            0,
            f"expected state {expected.value!r}, observed {observed.value!r}",
        )


@dataclass(frozen=True)
class ServiceInfo:
    """Structured description of observed and desired service state."""

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
    """Backend contract for service inspection and predefined lifecycle actions."""

    def list_services(self) -> list[ServiceInfo]:
        ...

    def get_status(self, name: str) -> ServiceInfo:
        ...

    def start(self, name: str) -> ServiceInfo:
        ...

    def stop(self, name: str) -> ServiceInfo:
        ...

    def restart(self, name: str) -> ServiceInfo:
        ...
