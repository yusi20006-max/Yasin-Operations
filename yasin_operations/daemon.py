"""Minimal long-running entrypoint for a supervised Operations service."""
from __future__ import annotations

import os
import signal
import time

from yasin_operations.cli import build_runtime
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.safety.classification import SafetyClass


_STOP = False


def _stop(_signum: int, _frame: object) -> None:
    global _STOP
    _STOP = True


def main() -> int:
    interval = max(1.0, float(os.environ.get("YASIN_OPERATIONS_HEALTH_INTERVAL_SECONDS", "60")))
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    executor, _, _ = build_runtime()
    while not _STOP:
        executor.execute(
            Operation(
                name="health_check",
                target=OperationTarget(kind="self", identifier="runtime"),
                safety_class=SafetyClass.READ_ONLY,
            ),
            actor="daemon",
            source="daemon.health",
        )
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
