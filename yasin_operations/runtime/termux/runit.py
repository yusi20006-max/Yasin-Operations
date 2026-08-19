"""Optional runit adapter for Termux/Linux.

Only predefined service names are accepted. Commands are constructed from
fixed argv lists; no shell strings or arbitrary user commands are exposed.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from yasin_operations.runtime.process import ProcessInspector
from yasin_operations.runtime.service import ServiceBackend, ServiceCommandError, ServiceInfo, ServiceNotFoundError, ServiceState


@dataclass(frozen=True)
class RunitServiceDefinition:
    name: str
    process_pattern: str = ""
    service_dir: str = ""
    desired_state: ServiceState = ServiceState.RUNNING
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("service name must not be empty")
        if self.service_dir and not self.service_dir.startswith("/"):
            raise ValueError("service_dir must be absolute")


_RUNIT_STATUS_RE = re.compile(r"^(?P<state>run|down|fail|timeout|finish):(?:\s+|$)", re.IGNORECASE)


def _normalize_runit_status(output: str, returncode: int) -> ServiceState:
    """Normalize authoritative ``sv status`` output.

    Runit status uses a textual state prefix.  The command's exit code is not
    sufficient because ``sv status`` can return success while reporting a
    service as ``down`` (for example ``down: ...: normally up``).
    """
    match = _RUNIT_STATUS_RE.match((output or "").lstrip())
    if match:
        state = match.group("state").lower()
        if state == "run":
            return ServiceState.RUNNING
        if state == "down":
            return ServiceState.STOPPED
        if state in {"fail", "timeout"}:
            return ServiceState.FAILED
        return ServiceState.UNKNOWN
    return ServiceState.UNKNOWN


class RunitServiceBackend(ServiceBackend):
    """Observe and control registered runit services using fixed argv."""

    def __init__(self, inspector: ProcessInspector, service_root: str = "/data/data/com.termux/files/usr/var/service", definitions: Optional[Sequence[RunitServiceDefinition]] = None, timeout: float = 10.0, sv_path: Optional[str] = None) -> None:
        self._inspector = inspector
        self._root = Path(service_root)
        self._timeout = timeout
        self._sv_path = Path(sv_path or os.environ.get("YASIN_OPERATIONS_SV", "/data/data/com.termux/files/usr/bin/sv"))
        self._defs = {d.name: d for d in (definitions or ())}

    @property
    def available(self) -> bool:
        return self._root.is_dir() and self._sv_path.is_file() and os.access(self._sv_path, os.X_OK)

    def register(self, definition: RunitServiceDefinition) -> None:
        self._defs[definition.name] = definition

    def list_services(self) -> list[ServiceInfo]:
        return [self.get_status(name) for name in sorted(self._defs)]

    def get_status(self, name: str) -> ServiceInfo:
        d = self._require(name)
        if not self.available:
            return ServiceInfo(name=name, state=ServiceState.UNKNOWN, desired_state=d.desired_state, health_state="unavailable", message="runit adapter unavailable", extra={"adapter": "termux-runit"})
        result = self._sv(d, "status")
        status_text = (result.stdout or result.stderr or "").strip()
        state = _normalize_runit_status(status_text, result.returncode)
        matches = self._inspector.find_by_name(d.process_pattern) if d.process_pattern else []
        pid = min((p.pid for p in matches), default=None) if state == ServiceState.RUNNING else None
        health = {
            ServiceState.RUNNING: "ok",
            ServiceState.STOPPED: "stopped",
            ServiceState.FAILED: "failed",
            ServiceState.DEGRADED: "degraded",
            ServiceState.UNKNOWN: "unknown",
        }.get(state, "unknown")
        return ServiceInfo(name=name, state=state, pid=pid, desired_state=d.desired_state, health_state=health, message=status_text[:200] or None, extra={"adapter": "termux-runit", "service_dir": d.service_dir or str(self._root / name), "runit_returncode": result.returncode})

    def start(self, name: str) -> ServiceInfo:
        return self._mutate(name, "up")

    def stop(self, name: str) -> ServiceInfo:
        return self._mutate(name, "down")

    def restart(self, name: str) -> ServiceInfo:
        d = self._require(name)
        if not self.available:
            return self.get_status(name)
        self._run_command(d, "restart")
        return self.get_status(name)

    def _mutate(self, name: str, action: str) -> ServiceInfo:
        d = self._require(name)
        if not self.available:
            return self.get_status(name)
        self._run_command(d, action)
        return self.get_status(name)

    def _run_command(self, d: RunitServiceDefinition, action: str) -> subprocess.CompletedProcess[str]:
        result = self._sv(d, action)
        if result.returncode != 0:
            output = (result.stderr or result.stdout or "").strip()[:500]
            raise ServiceCommandError(d.name, action, result.returncode, output)
        return result

    def _sv(self, d: RunitServiceDefinition, action: str) -> subprocess.CompletedProcess[str]:
        service_dir = d.service_dir or str(self._root / d.name)
        if not Path(service_dir).is_dir():
            raise ServiceNotFoundError(d.name)
        return subprocess.run([str(self._sv_path), action, service_dir], capture_output=True, text=True, timeout=self._timeout, check=False)

    def _require(self, name: str) -> RunitServiceDefinition:
        if name not in self._defs:
            raise ServiceNotFoundError(name)
        return self._defs[name]
