"""Internal backend errors mapped to OperationError by the tools layer."""

from __future__ import annotations


class BackendError(Exception):
    def __init__(self, service: str, message: str):
        self.service = service
        self.message = message
        super().__init__(f"{service}: {message}")


class ActionNotConfiguredError(BackendError):
    def __init__(self, service: str, action: str):
        super().__init__(service, f"action {action!r} is not configured")
        self.action = action


class BackendExecutionError(BackendError):
    pass


class BackendTimeoutError(BackendError):
    def __init__(self, service: str, action: str):
        super().__init__(service, f"action {action!r} timed out")
        self.action = action


class BackendPermissionError(BackendError):
    pass
