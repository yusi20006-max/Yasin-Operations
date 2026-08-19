"""Backward-compatible Termux runtime configuration facade."""
from __future__ import annotations

from yasin_operations.config.config import (
    DEFAULT_SERVICE_ROOT,
    DEFAULT_SV_PATH,
    OperationsConfig,
    load_config,
)


class TermuxRuntimeConfig(OperationsConfig):
    """Compatibility name for the shared operations configuration."""

    @classmethod
    def from_env(cls) -> "TermuxRuntimeConfig":
        config = load_config()
        return cls(
            service_root=config.service_root,
            sv_path=config.sv_path,
            service_names=config.service_names,
            execution_timeout_seconds=config.execution_timeout_seconds,
            startup_grace_seconds=config.startup_grace_seconds,
            always_on=config.always_on,
            log_level=config.log_level,
        )
