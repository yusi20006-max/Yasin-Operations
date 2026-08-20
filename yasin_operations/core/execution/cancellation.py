"""Transport-neutral cooperative cancellation primitives."""
from __future__ import annotations

from dataclasses import dataclass
from threading import Event


class OperationCancelledError(Exception):
    """Raised when execution is cancelled at a cooperative checkpoint."""


@dataclass
class CancellationToken:
    """Thread-safe cancellation token shared by an execution request."""

    _event: Event

    @classmethod
    def create(cls) -> "CancellationToken":
        return cls(Event())

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise OperationCancelledError("operation execution was cancelled")
