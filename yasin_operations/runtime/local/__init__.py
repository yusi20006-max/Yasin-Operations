"""Local (Termux/Linux) runtime backends.

Uses Python standard library and controlled, fixed-argument
subprocess calls only. Does not expose unrestricted shell or
user-supplied command execution.
"""

from yasin_operations.runtime.local.process_backend import LocalProcessInspector
from yasin_operations.runtime.local.service_backend import (
    LocalServiceBackend,
    ServiceDefinition,
)

__all__ = [
    "LocalProcessInspector",
    "LocalServiceBackend",
    "ServiceDefinition",
]
