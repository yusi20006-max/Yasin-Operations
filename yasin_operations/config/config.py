"""Validated, layered configuration for Yasin-Operations.

Configuration precedence is deterministic:

1. built-in safe defaults
2. environment variables
3. explicit overrides supplied by the caller/CLI

The module deliberately avoids a third-party configuration dependency and
keeps filesystem validation non-destructive: service names are validated as
identifiers, while existence checks are exposed separately for diagnostics.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from yasin_operations.runtime.termux.runit import RunitServiceDefinition


DEFAULT_SERVICE_ROOT = "/data/data/com.termux/files/usr/var/service"
DEFAULT_SV_PATH = "/data/data/com.termux/files/usr/bin/sv"
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 30.0
DEFAULT_STARTUP_GRACE_SECONDS = 2.0
DEFAULT_ALWAYS_ON = True
DEFAULT_SERVICE_NAMES: tuple[str, ...] = ()


class InvalidConfigurationError(ValueError):
    """Raised when a configuration value fails validation."""


@dataclass(frozen=True)
class OperationsConfig:
    """Runtime configuration shared by the CLI and Termux adapter."""

    service_root: str = DEFAULT_SERVICE_ROOT
    sv_path: str = DEFAULT_SV_PATH
    service_names: tuple[str, ...] = DEFAULT_SERVICE_NAMES
    execution_timeout_seconds: float = DEFAULT_EXECUTION_TIMEOUT_SECONDS
    startup_grace_seconds: float = DEFAULT_STARTUP_GRACE_SECONDS
    always_on: bool = DEFAULT_ALWAYS_ON
    log_level: str = "INFO"

    _VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

    def __post_init__(self) -> None:
        for field_name in ("service_root", "sv_path"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidConfigurationError(f"{field_name} must be a non-empty string")
            if not Path(value).is_absolute():
                raise InvalidConfigurationError(f"{field_name} must be an absolute path, got {value!r}")

        if self.execution_timeout_seconds <= 0:
            raise InvalidConfigurationError(
                "execution_timeout_seconds must be positive, "
                f"got {self.execution_timeout_seconds!r}"
            )
        if self.startup_grace_seconds < 0:
            raise InvalidConfigurationError(
                "startup_grace_seconds must not be negative, "
                f"got {self.startup_grace_seconds!r}"
            )

        if not isinstance(self.always_on, bool):
            raise InvalidConfigurationError("always_on must be a boolean")
        if not isinstance(self.service_names, tuple):
            raise InvalidConfigurationError("service_names must be a tuple of strings")
        for name in self.service_names:
            if not isinstance(name, str) or not name.strip():
                raise InvalidConfigurationError("service_names must not contain empty names")
            if name.strip() != name or any(char in name for char in "/\\"):
                raise InvalidConfigurationError(
                    f"service name must be a simple runit name, got {name!r}"
                )
        if self.log_level not in self._VALID_LOG_LEVELS:
            raise InvalidConfigurationError(
                f"log_level must be one of {sorted(self._VALID_LOG_LEVELS)}, "
                f"got {self.log_level!r}"
            )

    def service_definitions(self) -> tuple[RunitServiceDefinition, ...]:
        """Build safe service definitions from the configured registry."""
        return tuple(
            RunitServiceDefinition(name=name, process_pattern=name)
            for name in self.service_names
        )

    def missing_services(self) -> tuple[str, ...]:
        """Return registered services that are absent from the service root."""
        root = Path(self.service_root)
        return tuple(name for name in self.service_names if not (root / name).exists())

    def with_overrides(self, **overrides: object) -> "OperationsConfig":
        """Return a validated copy with explicit caller/CLI overrides."""
        unknown = set(overrides) - set(self.__dataclass_fields__)
        if unknown:
            raise InvalidConfigurationError(
                f"unknown configuration override(s): {', '.join(sorted(unknown))}"
            )
        normalized = dict(overrides)
        if "service_names" in normalized and isinstance(normalized["service_names"], list):
            normalized["service_names"] = tuple(normalized["service_names"])
        return replace(self, **normalized)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        raise InvalidConfigurationError(
            f"Environment variable {name} must be a number, got {raw!r}"
        ) from None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise InvalidConfigurationError(
        f"Environment variable {name} must be a boolean (true/false), got {raw!r}"
    )


def _env_services(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, "")
    return tuple(sorted({item.strip() for item in raw.split(",") if item.strip()}))


def load_config(overrides: Mapping[str, object] | None = None) -> OperationsConfig:
    """Load defaults, apply environment configuration, then explicit overrides."""
    config = OperationsConfig(
        service_root=os.environ.get("YASIN_OPERATIONS_SERVICE_ROOT", DEFAULT_SERVICE_ROOT),
        sv_path=os.environ.get("YASIN_OPERATIONS_SV_PATH", DEFAULT_SV_PATH),
        service_names=_env_services("YASIN_OPERATIONS_SERVICE_NAMES"),
        execution_timeout_seconds=_env_float(
            "YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS",
            DEFAULT_EXECUTION_TIMEOUT_SECONDS,
        ),
        startup_grace_seconds=_env_float(
            "YASIN_OPERATIONS_STARTUP_GRACE_SECONDS",
            DEFAULT_STARTUP_GRACE_SECONDS,
        ),
        always_on=_env_bool("YASIN_OPERATIONS_ALWAYS_ON", DEFAULT_ALWAYS_ON),
        log_level=os.environ.get("YASIN_OPERATIONS_LOG_LEVEL", "INFO"),
    )
    if overrides:
        config = config.with_overrides(**dict(overrides))
    return config
