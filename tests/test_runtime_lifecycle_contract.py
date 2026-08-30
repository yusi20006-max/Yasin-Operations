"""Production-facing lifecycle contract tests.

These tests intentionally exercise command-success-without-readiness,
timeouts, unavailable backends, stale process state, and service isolation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from yasin_operations.runtime.local.service_backend import LocalServiceBackend, ServiceDefinition
from yasin_operations.runtime.service import (
    ServiceReadinessError,
    ServiceState,
    ServiceTimeoutError,
)
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition


class EmptyInspector:
    def find_by_name(self, pattern: str):
        return []

    def is_alive(self, pid: int) -> bool:
        return False


def _runit_fixture(tmp_path: Path, *, initial_state: str = "down", command: str = "normal"):
    root = tmp_path / "services"
    root.mkdir()
    (root / "demo").mkdir()
    (root / "broken").mkdir()
    state = tmp_path / "state"
    state.write_text(initial_state, encoding="utf-8")
    script = tmp_path / "sv"
    script.write_text(
        "#!/bin/sh\n"
        "action=\"$1\"\n"
        "if [ \"$action\" = status ]; then\n"
        "  state=$(cat \"%s\")\n"
        "  echo \"$state: demo\"\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"%s\" = timeout ]; then sleep 2; exit 0; fi\n"
        "if [ \"$action\" = up ] && [ \"%s\" = normal ]; then echo run > \"%s\"; fi\n"
        "if [ \"$action\" = down ] && [ \"%s\" = normal ]; then echo down > \"%s\"; fi\n"
        "exit 0\n"
        % (state, command, command, state, command, state),
        encoding="utf-8",
    )
    script.chmod(0o755)
    definitions = [
        RunitServiceDefinition("demo", process_pattern=""),
        RunitServiceDefinition("broken", service_dir=str(root / "missing")),
    ]
    return root, state, script, definitions


def test_runit_successful_control_command_must_reach_requested_state(tmp_path: Path):
    root, state, script, definitions = _runit_fixture(tmp_path, command="noop")
    backend = RunitServiceBackend(
        EmptyInspector(), str(root), definitions[:1], timeout=0.05, startup_grace=0, poll_interval=0.01, sv_path=str(script)
    )

    with pytest.raises(ServiceTimeoutError):
        backend.start("demo")
    assert state.read_text(encoding="utf-8") == "down"


def test_runit_control_timeout_is_typed(tmp_path: Path):
    root, _state, script, definitions = _runit_fixture(tmp_path, command="timeout")
    backend = RunitServiceBackend(
        EmptyInspector(), str(root), definitions[:1], timeout=0.02, startup_grace=0, poll_interval=0.01, sv_path=str(script)
    )

    with pytest.raises(ServiceTimeoutError) as exc:
        backend.start("demo")
    assert exc.value.name == "demo"
    assert isinstance(exc.value, TimeoutError)


def test_runit_unavailable_mutation_never_reports_success(tmp_path: Path):
    root = tmp_path / "services"
    root.mkdir()
    (root / "demo").mkdir()
    backend = RunitServiceBackend(
        EmptyInspector(), str(root), [RunitServiceDefinition("demo")], timeout=0.05, sv_path=str(tmp_path / "missing-sv")
    )

    with pytest.raises(ServiceTimeoutError):
        backend.stop("demo")


def test_runit_status_discovery_isolated_per_service(tmp_path: Path):
    root, _state, script, definitions = _runit_fixture(tmp_path)
    backend = RunitServiceBackend(EmptyInspector(), str(root), definitions, timeout=0.1, sv_path=str(script))

    services = {item.name: item for item in backend.list_services()}
    assert services["demo"].state is ServiceState.STOPPED
    # Missing service directory is isolated and classified as missing, not failed.
    assert services["broken"].state is ServiceState.UNKNOWN
    assert services["broken"].health_state == "missing"
    assert services["broken"].extra.get("presence") == "missing"


def test_local_backend_does_not_report_fast_crash_as_running(tmp_path: Path):
    backend = LocalServiceBackend(
        EmptyInspector(),
        [ServiceDefinition("demo", start_argv=(sys.executable, "-c", "raise SystemExit(0)"))],
        command_timeout_seconds=0.2,
        startup_grace_seconds=0,
        poll_interval_seconds=0.01,
    )

    with pytest.raises(ServiceReadinessError):
        backend.start("demo")


def test_local_backend_requires_stop_readiness(tmp_path: Path):
    backend = LocalServiceBackend(
        EmptyInspector(),
        [ServiceDefinition("demo")],
        command_timeout_seconds=0.05,
        startup_grace_seconds=0,
        poll_interval_seconds=0.01,
    )

    status = backend.get_status("demo")
    assert status.state is ServiceState.STOPPED
