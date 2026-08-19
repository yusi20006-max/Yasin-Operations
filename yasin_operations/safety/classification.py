"""Safety classification for operations.

This module only defines the classification the architecture needs
so a future safety/permission layer (Issue #4) can enforce policy.
It does not implement any enforcement itself, and it does not
implement or permit arbitrary shell/command execution.
"""

from __future__ import annotations

from enum import Enum


class SafetyClass(str, Enum):
    """Whether an operation only reads state or can change it.

    READ_ONLY: the operation must not mutate any external state
    (filesystem, service, database, network resource, etc).
    MUTATING: the operation may change external state and therefore
    requires stricter authorization once a permission layer exists.
    """

    READ_ONLY = "read_only"
    MUTATING = "mutating"
