from __future__ import annotations

import json
import os
import subprocess

from yasin_operations.cli import STATUS_EXIT_DEGRADED, _health_exit_code, _service_summary
from yasin_operations.runtime.service import ServiceState
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition


class FakeInspector:
    def __init__(self, pids: dict[str, list[int]] | None = None) -> None:
        self.pids = pids or {}

    def find_by_name(self, pattern: str):
        return [type("P", (), {"pid": pid})() for pid in self.pids.get(pattern, [])]

    def is_alive(self, pid: int) -> bool:
        return pid in {p.pid for values in self.pids.values() for p in [type("P", (), {"pid": pid})()]}


def _backend(tmp_path, monkeypatch, output: str, returncode: int = 0):
    service_root = tmp_path / "service"
    service_root.mkdir()
    service_dir = service_root / "yasinpress"
    service_dir.mkdir()
    sv = tmp_path / "sv"
    sv.write_text("#!/bin/sh\n")
    sv.chmod(sv.stat().st_mode | os.X_OK)

    completed = subprocess.CompletedProcess([str(sv), "status", str(service_dir)], returncode, output, "")
    monkeypatch.setattr("yasin_operations.runtime.termux.runit.subprocess.run", lambda *args, **kwargs: completed)
    inspector = FakeInspector({"yasinpress": [1234]})
    backend = RunitServiceBackend(
        inspector,
        service_root=str(service_root),
        sv_path=str(sv),
        definitions=[RunitServiceDefinition("yasinpress", process_pattern="yasinpress")],
    )
    return backend


def test_run_status_is_running_and_healthy(tmp_path, monkeypatch):
    backend = _backend(tmp_path, monkeypatch, "run: yasinpress: (pid 1234) 3s")
    info = backend.get_status("yasinpress")
    assert info.state is ServiceState.RUNNING
    assert info.health_state == "ok"
    assert info.pid == 1234
    assert info.desired_state is ServiceState.RUNNING


def test_down_status_is_stopped_even_when_svis_successful(tmp_path, monkeypatch):
    backend = _backend(tmp_path, monkeypatch, "down: yasinpress: 4s, normally up")
    info = backend.get_status("yasinpress")
    assert info.state is ServiceState.STOPPED
    assert info.health_state == "stopped"
    assert info.pid is None
    assert info.desired_state is ServiceState.RUNNING


def test_fail_and_timeout_status_are_failed(tmp_path, monkeypatch):
    for output in ("fail: yasinpress: 2s, normally up", "timeout: yasinpress: 2s"):
        backend = _backend(tmp_path, monkeypatch, output)
        info = backend.get_status("yasinpress")
        assert info.state is ServiceState.FAILED
        assert info.health_state == "failed"


def test_unknown_status_is_not_assumed_running(tmp_path, monkeypatch):
    backend = _backend(tmp_path, monkeypatch, "unexpected status output", returncode=0)
    info = backend.get_status("yasinpress")
    assert info.state is ServiceState.UNKNOWN
    assert info.health_state == "unknown"
    assert info.pid is None


def test_summary_marks_mixed_running_and_down_as_degraded():
    summary = _service_summary([
        {"name": "hermes-agent", "state": "running"},
        {"name": "yasin-ai", "state": "running"},
        {"name": "yasinpress", "state": "stopped"},
        {"name": "yasinrelay", "state": "running"},
    ])
    assert summary["counts"]["running"] == 3
    assert summary["counts"]["stopped"] == 1
    assert summary["health"] == "degraded"
    assert summary["exit_code"] == STATUS_EXIT_DEGRADED


def test_health_exit_code_tracks_corrected_service_summary():
    assert _health_exit_code({"status": "healthy"}, {"health": "degraded"}) == 1


def test_status_payload_remains_json_serializable(tmp_path, monkeypatch):
    backend = _backend(tmp_path, monkeypatch, "down: yasinpress: 1s, normally up")
    info = backend.get_status("yasinpress")
    payload = {
        "name": info.name,
        "state": info.state.value,
        "health_state": info.health_state,
        "desired_state": info.desired_state.value,
        "pid": info.pid,
    }
    assert json.loads(json.dumps(payload))["state"] == "stopped"
