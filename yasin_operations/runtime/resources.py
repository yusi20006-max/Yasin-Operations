"""Low-dependency CPU and memory diagnostics for the Operations process."""
from __future__ import annotations

import os
import resource
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSnapshot:
    pid: int
    rss_bytes: int | None
    user_cpu_seconds: float
    system_cpu_seconds: float
    load_average_1m: float | None
    timestamp: float

    def as_dict(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "rss_bytes": self.rss_bytes,
            "user_cpu_seconds": self.user_cpu_seconds,
            "system_cpu_seconds": self.system_cpu_seconds,
            "load_average_1m": self.load_average_1m,
            "timestamp": self.timestamp,
        }


def snapshot() -> ResourceSnapshot:
    """Return best-effort resource metrics on supported runtimes.

    Individual optional metrics degrade to ``None`` rather than making
    status/health commands fail on platforms where a metric is absent
    or inaccessible (including constrained Termux environments).
    """
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
    except (AttributeError, OSError, ValueError):
        usage = None

    rss_bytes: int | None = None
    user_cpu = 0.0
    system_cpu = 0.0
    if usage is not None:
        rss = getattr(usage, "ru_maxrss", None)
        if rss is not None:
            try:
                # Linux reports KiB; other POSIX systems may report bytes.
                rss_bytes = int(rss * 1024) if os.name == "posix" else int(rss)
            except (TypeError, ValueError, OverflowError):
                rss_bytes = None
        try:
            user_cpu = float(usage.ru_utime)
            system_cpu = float(usage.ru_stime)
        except (AttributeError, TypeError, ValueError):
            user_cpu = 0.0
            system_cpu = 0.0

    try:
        load = float(os.getloadavg()[0])
    except (AttributeError, OSError, IndexError, TypeError, ValueError):
        load = None

    return ResourceSnapshot(
        pid=os.getpid(),
        rss_bytes=rss_bytes,
        user_cpu_seconds=user_cpu,
        system_cpu_seconds=system_cpu,
        load_average_1m=load,
        timestamp=time.time(),
    )
