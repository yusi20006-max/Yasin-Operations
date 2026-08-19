"""Runtime Operations layer.

Concrete operational capabilities built on Core contracts.
Backends (local Termux/Linux, future systemd/runit, etc.) live
behind adapter boundaries; the Core remains generic and independent
of any specific process supervisor or external Yasin project.
"""

from yasin_operations.runtime.process import ProcessInfo, ProcessNotFoundError
from yasin_operations.runtime.service import (
    ServiceInfo,
    ServiceNotFoundError,
    ServiceState,
)
from yasin_operations.runtime.health import HealthCheckResult, HealthStatus
from yasin_operations.runtime.diagnostics import DiagnosticsSnapshot

__all__ = [
    "ProcessInfo",
    "ProcessNotFoundError",
    "ServiceInfo",
    "ServiceNotFoundError",
    "ServiceState",
    "HealthCheckResult",
    "HealthStatus",
    "DiagnosticsSnapshot",
]
