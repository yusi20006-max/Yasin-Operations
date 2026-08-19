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
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = getattr(usage, "ru_maxrss", None)
    if rss is not None:
        # Linux reports KiB; other platforms may report bytes.
        rss_bytes = int(rss * 1024) if os.name == "posix" else int(rss)
    else:
        rss_bytes = None
    try:
        load = float(os.getloadavg()[0])
    except (AttributeError, OSError):
        load = None
    return ResourceSnapshot(
        pid=os.getpid(),
        rss_bytes=rss_bytes,
        user_cpu_seconds=float(usage.ru_utime),
        system_cpu_seconds=float(usage.ru_stime),
        load_average_1m=load,
        timestamp=time.time(),
    )
