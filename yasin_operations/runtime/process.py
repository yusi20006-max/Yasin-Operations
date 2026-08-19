"""Process inspection abstraction.

Read-only view of local processes. Implementations must not expose
arbitrary shell execution; they may use controlled, predefined
mechanisms (e.g. /proc, fixed-argv ps) only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Protocol, runtime_checkable


class ProcessNotFoundError(Exception):
    """Raised when a requested process does not exist."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Process not found: {identifier!r}")


class InvalidPIDError(Exception):
    """Raised when a PID value is not a valid process identifier."""

    def __init__(self, value: object):
        self.value = value
        super().__init__(f"Invalid PID: {value!r}")


@dataclass(frozen=True)
class ProcessInfo:
    """Structured, read-only description of a process."""

    pid: int
    name: str
    status: str = "unknown"
    ppid: Optional[int] = None
    username: Optional[str] = None
    cmdline: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_rss_bytes: Optional[int] = None
    create_time: Optional[float] = None  # epoch seconds if available
    extra: Mapping[str, object] = field(default_factory=dict)

    def is_alive(self) -> bool:
        """Heuristic: a process reported by the inspector is treated as alive
        unless its status is explicitly a terminal state."""
        terminal = {"zombie", "dead", "gone"}
        return self.status.lower() not in terminal


@runtime_checkable
class ProcessInspector(Protocol):
    """Backend contract for process inspection.

    All methods are read-only. Implementations must convert expected
    failure modes into the typed exceptions above rather than leaking
    raw OS errors to callers of the Runtime tools layer.
    """

    def list_processes(self) -> list[ProcessInfo]:
        """Return currently visible processes."""
        ...

    def get_process(self, pid: int) -> ProcessInfo:
        """Return info for a single PID, or raise ProcessNotFoundError /
        InvalidPIDError."""
        ...

    def find_by_name(self, pattern: str) -> list[ProcessInfo]:
        """Return processes whose name or cmdline contains pattern
        (case-insensitive substring match)."""
        ...

    def is_alive(self, pid: int) -> bool:
        """Return True if the process exists and is not in a terminal state."""
        ...
