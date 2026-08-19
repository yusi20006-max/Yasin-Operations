"""Local service backend.

Services are registered via ServiceDefinition with predefined
start/stop argument lists. The backend never accepts arbitrary
user-supplied command strings — only the fixed argv sequences
associated with each definition.

Does not assume systemd, Docker, or any particular init system.
Suitable as a minimal Termux/Linux adapter; future backends can
implement the same ServiceBackend protocol for runit/systemd/etc.
"""

from __future__ import annotations

import signal
import subprocess
import time
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from yasin_operations.runtime.process import ProcessInspector, ProcessNotFoundError
from yasin_operations.runtime.service import (
    ServiceBackend,
    ServiceInfo,
    ServiceNotFoundError,
    ServiceState,
)


@dataclass(frozen=True)
class ServiceDefinition:
    """Pre-declared service with fixed, validated action commands.

    start_argv / stop_argv are argument lists (no shell).
    process_pattern is used to locate the running process by name/cmdline
    when PID is not tracked.
    """

    name: str
    process_pattern: str = ""
    start_argv: Optional[Sequence[str]] = None
    stop_argv: Optional[Sequence[str]] = None
    stop_signal: int = signal.SIGTERM
    desired_state: ServiceState = ServiceState.RUNNING
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("ServiceDefinition.name must not be empty")
        if self.start_argv is not None:
            if not all(isinstance(a, str) for a in self.start_argv):
                raise ValueError("start_argv must be a sequence of strings")
        if self.stop_argv is not None:
            if not all(isinstance(a, str) for a in self.stop_argv):
                raise ValueError("stop_argv must be a sequence of strings")


class LocalServiceBackend:
    """In-process registry of ServiceDefinitions + process inspection."""

    def __init__(
        self,
        inspector: ProcessInspector,
        definitions: Optional[Sequence[ServiceDefinition]] = None,
        command_timeout_seconds: float = 15.0,
    ) -> None:
        self._inspector = inspector
        self._defs: dict[str, ServiceDefinition] = {}
        self._timeout = command_timeout_seconds
        self._tracked_pids: dict[str, int] = {}
        if definitions:
            for d in definitions:
                self.register(d)

    def register(self, definition: ServiceDefinition) -> None:
        self._defs[definition.name] = definition

    def unregister(self, name: str) -> None:
        self._defs.pop(name, None)
        self._tracked_pids.pop(name, None)

    def list_services(self) -> list[ServiceInfo]:
        return [self.get_status(name) for name in sorted(self._defs)]

    def get_status(self, name: str) -> ServiceInfo:
        definition = self._require(name)
        pid = self._resolve_pid(definition)
        if pid is not None and self._inspector.is_alive(pid):
            return ServiceInfo(
                name=name,
                state=ServiceState.RUNNING,
                pid=pid,
                desired_state=definition.desired_state,
                health_state="ok",
                message="process is alive",
            )
        return ServiceInfo(
            name=name,
            state=ServiceState.STOPPED,
            pid=None,
            desired_state=definition.desired_state,
            health_state="stopped",
            message="no matching live process",
        )

    def start(self, name: str) -> ServiceInfo:
        definition = self._require(name)
        current = self.get_status(name)
        if current.state == ServiceState.RUNNING:
            return current
        if definition.start_argv is None:
            from yasin_operations.runtime.local._errors import ActionNotConfiguredError

            raise ActionNotConfiguredError(name, "start")
        try:
            proc = subprocess.Popen(
                list(definition.start_argv),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            from yasin_operations.runtime.local._errors import BackendExecutionError

            raise BackendExecutionError(name, f"start binary not found: {exc}") from exc
        except OSError as exc:
            from yasin_operations.runtime.local._errors import BackendExecutionError

            raise BackendExecutionError(name, f"start failed: {exc}") from exc
        self._tracked_pids[name] = proc.pid
        time.sleep(0.05)
        return self.get_status(name)

    def stop(self, name: str) -> ServiceInfo:
        definition = self._require(name)
        current = self.get_status(name)
        if current.state == ServiceState.STOPPED:
            return current
        if definition.stop_argv is not None:
            try:
                completed = subprocess.run(
                    list(definition.stop_argv),
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                    check=False,
                )
                if completed.returncode != 0:
                    from yasin_operations.runtime.local._errors import BackendExecutionError

                    raise BackendExecutionError(
                        name,
                        f"stop command exited {completed.returncode}: "
                        f"{(completed.stderr or completed.stdout or '').strip()[:200]}",
                    )
            except subprocess.TimeoutExpired as exc:
                from yasin_operations.runtime.local._errors import BackendTimeoutError

                raise BackendTimeoutError(name, "stop") from exc
            except FileNotFoundError as exc:
                from yasin_operations.runtime.local._errors import BackendExecutionError

                raise BackendExecutionError(name, f"stop binary not found: {exc}") from exc
        else:
            pid = current.pid or self._tracked_pids.get(name)
            if pid is None:
                return current
            try:
                os_kill = __import__("os").kill
                os_kill(pid, definition.stop_signal)
            except ProcessLookupError:
                pass
            except PermissionError as exc:
                from yasin_operations.runtime.local._errors import BackendPermissionError

                raise BackendPermissionError(name, str(exc)) from exc
            except OSError as exc:
                from yasin_operations.runtime.local._errors import BackendExecutionError

                raise BackendExecutionError(name, f"stop signal failed: {exc}") from exc
        self._tracked_pids.pop(name, None)
        time.sleep(0.05)
        return self.get_status(name)

    def restart(self, name: str) -> ServiceInfo:
        self.stop(name)
        return self.start(name)

    def _require(self, name: str) -> ServiceDefinition:
        if name not in self._defs:
            raise ServiceNotFoundError(name)
        return self._defs[name]

    def _resolve_pid(self, definition: ServiceDefinition) -> Optional[int]:
        tracked = self._tracked_pids.get(definition.name)
        if tracked is not None and self._inspector.is_alive(tracked):
            return tracked
        if not definition.process_pattern:
            return None
        matches = self._inspector.find_by_name(definition.process_pattern)
        if not matches:
            return None
        return min(m.pid for m in matches)
