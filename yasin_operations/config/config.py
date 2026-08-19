"""Minimal configuration abstraction.

Kept intentionally small: defaults, environment-variable overrides,
and explicit-construction, with validation. No config files, no
remote config sources -- those would be premature for this
foundation issue.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class InvalidConfigurationError(Exception):
    """Raised when a configuration value fails validation."""


@dataclass(frozen=True)
class OperationsConfig:
    """Core configuration for Yasin-Operations.

    execution_timeout_seconds: a soft upper bound future executors
    may use to bound a single operation attempt. Not enforced by
    Executor itself in this issue (no timeout mechanism is wired up
    yet) -- it exists here so the config surface is stable for when
    that lands.
    log_level: a plain string, validated against a known set, so a
    typo fails fast rather than silently doing nothing.
    """

    execution_timeout_seconds: int = 30
    log_level: str = "INFO"

    _VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

    def __post_init__(self) -> None:
        if self.execution_timeout_seconds <= 0:
            raise InvalidConfigurationError(
                "execution_timeout_seconds must be a positive integer, "
                f"got {self.execution_timeout_seconds!r}"
            )
        if self.log_level not in self._VALID_LOG_LEVELS:
            raise InvalidConfigurationError(
                f"log_level must be one of {sorted(self._VALID_LOG_LEVELS)}, "
                f"got {self.log_level!r}"
            )


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise InvalidConfigurationError(
            f"Environment variable {name} must be an integer, got {raw!r}"
        ) from None


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def load_config() -> OperationsConfig:
    """Build configuration from the environment, falling back to defaults.

    Recognized environment variables:
    - YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS
    - YASIN_OPERATIONS_LOG_LEVEL
    """
    return OperationsConfig(
        execution_timeout_seconds=_env_int(
            "YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS", 30
        ),
        log_level=_env_str("YASIN_OPERATIONS_LOG_LEVEL", "INFO"),
    )
