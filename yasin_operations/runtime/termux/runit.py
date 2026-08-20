"""Termux/runit service backend with verified lifecycle semantics.

Only predefined service names/actions are accepted. Commands use fixed argv;
no shell strings or arbitrary user commands are exposed.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from yasin_operations.runtime.process import ProcessInspector
from yasin_operations.runtime.service import (
    ServiceBackend,
    ServiceCommandError,
    ServiceInfo,
    ServiceNotFoundError,
    ServiceReadinessError,
    ServiceState,
    ServiceTimeoutError,
)

DEFAULT_STATE = ServiceState.UNKNOWN
_STATUS_PREFIXES = {
    "run": ServiceState.RUNNING,
    "down": ServiceState.STOPPED,
    "finish": ServiceState.STOPPED,
    "fail": ServiceState.FAILED,
    "timeout": ServiceState.FAILED,
}
_STATUS_RE = re.compile(r"^(?P<state>run|down|finish|fail|timeout|supervise):\s*")


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


class RunitServiceBackend(ServiceBackend):
    """Observe/control registered runit services using fixed argv and readiness polling."""

    def __init__(
        self,
        inspector: ProcessInspector,
        service_root: str = "/data/data/com.termux/files/usr/var/service",
        definitions: Optional[Sequence[RunitServiceDefinition]] = None,
        timeout: float = 10.0,
        startup_grace: float = 2.0,
        poll_interval: float = 0.05,
        sv_path: Optional[str] = None,
    ) -> None:
        if timeout <= 0 or startup_grace < 0 or poll_interval <= 0:
            raise ValueError("invalid runit lifecycle timing configuration")
        self._inspector = inspector
        self._root = Path(service_root)
        self._timeout = timeout
        self._startup_grace = startup_grace
        self._poll_interval = poll_interval
        self._sv_path = Path(
            sv_path or os.environ.get("YASIN_OPERATIONS_SV", "/data/data/com.termux/files/usr/bin/sv")
        )
        self._defs = {d.name: d for d in (definitions or ())}

    @property
    def available(self) -> bool:
        return self._root.is_dir() and self._sv_path.is_file() and os.access(self._sv_path, os.X_OK)

    def register(self, definition: RunitServiceDefinition) -> None:
        self._defs[definition.name] = definition

    def list_services(self) -> list[ServiceInfo]:
        results: list[ServiceInfo] = []
        for name in sorted(self._defs):
            # One bad service must not hide every other service from diagnostics.
            try:
                results.append(self.get_status(name))
            except (ServiceNotFoundError, ServiceCommandError) as exc:
                d = self._defs[name]
                results.append(
                    ServiceInfo(
                        name=name,
                        state=ServiceState.FAILED,
                        desired_state=d.desired_state,
                        health_state="failed",
                        message=str(exc)[:200],
                        extra={"adapter": "termux-runit", "error": type(exc).__name__},
                    )
                )
        return results

    def get_status(self, name: str) -> ServiceInfo:
        d = self._require(name)
        if not self.available:
            return ServiceInfo(
                name=name,
                state=ServiceState.UNKNOWN,
                desired_state=d.desired_state,
                health_state="unavailable",
                message="runit adapter unavailable",
                extra={"adapter": "termux-runit", "service_dir": d.service_dir or str(self._root / name)},
            )
        result = self._sv(d, "status")
        state = self._normalize_status(result.stdout, result.stderr, result.returncode)
        matches = self._inspector.find_by_name(d.process_pattern) if d.process_pattern and state == ServiceState.RUNNING else []
        pid = min((p.pid for p in matches), default=None)
        health_state = self._health_for(state, d.desired_state)
        output = (result.stdout or result.stderr or "").strip()
        return ServiceInfo(
            name=name,
            state=state,
            pid=pid,
            desired_state=d.desired_state,
            health_state=health_state,
            message=output[:200] or None,
            extra={"adapter": "termux-runit", "service_dir": d.service_dir or str(self._root / name)},
        )

    @staticmethod
    def _normalize_status(stdout: str, stderr: str, returncode: int) -> ServiceState:
        output = (stdout or stderr or "").strip()
        first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
        match = _STATUS_RE.match(first_line)
        if match:
            return _STATUS_PREFIXES.get(match.group("state"), DEFAULT_STATE)
        return ServiceState.UNKNOWN

    @staticmethod
    def _health_for(state: ServiceState, desired: ServiceState) -> str:
        if state is ServiceState.UNKNOWN:
            return "unknown"
        if state is ServiceState.FAILED:
            return "failed"
        if desired is ServiceState.RUNNING:
            return "ok" if state is ServiceState.RUNNING else "stopped"
        if desired is ServiceState.STOPPED:
            return "ok" if state is ServiceState.STOPPED else "degraded"
        return "degraded"

    def start(self, name: str) -> ServiceInfo:
        return self._mutate_and_verify(name, "up", ServiceState.RUNNING)

    def stop(self, name: str) -> ServiceInfo:
        return self._mutate_and_verify(name, "down", ServiceState.STOPPED)

    def restart(self, name: str) -> ServiceInfo:
        d = self._require(name)
        if not self.available:
            raise ServiceTimeoutError(name, "restart", "runit adapter unavailable; mutation not attempted")
        self._run_command(d, "restart")
        return self._wait_for_state(name, "restart", ServiceState.RUNNING)

    def _mutate_and_verify(self, name: str, action: str, expected: ServiceState) -> ServiceInfo:
        d = self._require(name)
        if not self.available:
            raise ServiceTimeoutError(name, action, "runit adapter unavailable; mutation not attempted")
        self._run_command(d, action)
        return self._wait_for_state(name, action, expected)

    def _wait_for_state(self, name: str, action: str, expected: ServiceState) -> ServiceInfo:
        deadline = time.monotonic() + self._timeout + self._startup_grace
        last = self.get_status(name)
        while time.monotonic() < deadline:
            if last.state is expected:
                return last
            if last.state is ServiceState.FAILED:
                raise ServiceReadinessError(name, action, expected, last.state)
            time.sleep(self._poll_interval)
            last = self.get_status(name)
        raise ServiceTimeoutError(
            name,
            action,
            f"timed out waiting for {expected.value!r}; observed {last.state.value!r}",
        )

    def _run_command(self, d: RunitServiceDefinition, action: str) -> subprocess.CompletedProcess[str]:
        try:
            result = self._sv(d, action)
        except subprocess.TimeoutExpired as exc:
            raise ServiceTimeoutError(d.name, action, "runit control command timed out") from exc
        if result.returncode != 0:
            output = (result.stderr or result.stdout or "").strip()[:500]
            raise ServiceCommandError(d.name, action, result.returncode, output)
        return result

    def _sv(self, d: RunitServiceDefinition, action: str) -> subprocess.CompletedProcess[str]:
        service_dir = d.service_dir or str(self._root / d.name)
        if not Path(service_dir).is_dir():
            raise ServiceNotFoundError(d.name)
        return subprocess.run(
            [str(self._sv_path), action, service_dir],
            capture_output=True,
            text=True,
            timeout=self._timeout,
            check=False,
        )

    def _require(self, name: str) -> RunitServiceDefinition:
        if name not in self._defs:
            raise ServiceNotFoundError(name)
        return self._defs[name]
