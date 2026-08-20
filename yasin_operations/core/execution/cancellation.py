"""Cooperative cancellation primitives for operation execution.

Cancellation is intentionally transport-neutral. The Executor checks the token
before execution and between retries; synchronous tools cannot be forcibly
preempted safely, so a cancellation observed after a tool returns is treated
according to the operation's outcome semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event


class OperationCancelled(Exception):
    """Raised at an Executor cancellation checkpoint."""


@dataclass
class CancellationToken:
    """Thread-safe, cooperative cancellation token."""

    _event: Event = field(default_factory=Event, repr=False)

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise OperationCancelled("operation cancellation requested")
