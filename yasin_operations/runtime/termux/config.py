"""Termux deployment configuration with safe environment overrides."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from yasin_operations.runtime.termux.runit import RunitServiceDefinition


DEFAULT_SERVICE_ROOT = "/data/data/com.termux/files/usr/var/service"
DEFAULT_SV_PATH = "/data/data/com.termux/files/usr/bin/sv"


@dataclass(frozen=True)
class TermuxRuntimeConfig:
    service_root: str = DEFAULT_SERVICE_ROOT
    sv_path: str = DEFAULT_SV_PATH
    service_names: tuple[str, ...] = ()
    execution_timeout_seconds: float = 30.0
    startup_grace_seconds: float = 2.0
    always_on: bool = True
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not Path(self.service_root).is_absolute():
            raise ValueError("service_root must be absolute")
        if not Path(self.sv_path).is_absolute():
            raise ValueError("sv_path must be absolute")
        if self.execution_timeout_seconds <= 0:
            raise ValueError("execution_timeout_seconds must be positive")
        if self.startup_grace_seconds < 0:
            raise ValueError("startup_grace_seconds must not be negative")
        if any(not name.strip() for name in self.service_names):
            raise ValueError("service_names must not contain empty names")

    @classmethod
    def from_env(cls) -> "TermuxRuntimeConfig":
        names = tuple(
            sorted(
                {
                    name.strip()
                    for name in os.environ.get("YASIN_OPERATIONS_SERVICE_NAMES", "").split(",")
                    if name.strip()
                }
            )
        )
        return cls(
            service_root=os.environ.get("YASIN_OPERATIONS_SERVICE_ROOT", DEFAULT_SERVICE_ROOT),
            sv_path=os.environ.get("YASIN_OPERATIONS_SV_PATH", DEFAULT_SV_PATH),
            service_names=names,
            execution_timeout_seconds=float(
                os.environ.get("YASIN_OPERATIONS_EXECUTION_TIMEOUT_SECONDS", "30")
            ),
            startup_grace_seconds=float(
                os.environ.get("YASIN_OPERATIONS_STARTUP_GRACE_SECONDS", "2")
            ),
            always_on=os.environ.get("YASIN_OPERATIONS_ALWAYS_ON", "1").strip().lower()
            not in {"0", "false", "no", "off"},
        )

    def service_definitions(self) -> tuple[RunitServiceDefinition, ...]:
        """Build fixed service definitions from names only.

        The adapter never reads or modifies the target service scripts.
        """
        return tuple(
            RunitServiceDefinition(name=name, process_pattern=name)
            for name in self.service_names
        )
