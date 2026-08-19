"""Issue #3 Termux/runit adapter tests."""
from __future__ import annotations

from pathlib import Path

from yasin_operations.runtime.process import ProcessInfo
from yasin_operations.runtime.service import ServiceState, ServiceNotFoundError
from yasin_operations.runtime.termux.diagnostics import detect_termux
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition


class FakeInspector:
    def __init__(self, matches=None):
        self.matches = matches or []

    def list_processes(self):
        return self.matches

    def get_process(self, pid: int):
        return next(p for p in self.matches if p.pid == pid)

    def find_by_name(self, pattern: str):
        return [p for p in self.matches if pattern.lower() in (p.name + " " + (p.cmdline or "")).lower()]

    def is_alive(self, pid: int):
        return any(p.pid == pid for p in self.matches)


def _backend(tmp_path: Path, inspector=None):
    service_root = tmp_path / "service"
    service_root.mkdir()
    (service_root / "demo").mkdir()
    sv = tmp_path / "sv"
    sv.write_text("#!/bin/sh\n", encoding="utf-8")
    sv.chmod(0o755)
    return RunitServiceBackend(inspector or FakeInspector(), str(service_root), [RunitServiceDefinition("demo", process_pattern="demo")], sv_path=str(sv))


def test_missing_runit_is_graceful(tmp_path: Path):
    backend = RunitServiceBackend(FakeInspector(), str(tmp_path), [RunitServiceDefinition("demo")], sv_path=str(tmp_path / "missing-sv"))
    info = backend.get_status("demo")
    assert info.state == ServiceState.UNKNOWN
    assert info.health_state == "unavailable"


def test_unknown_service_is_structured():
    backend = RunitServiceBackend(FakeInspector(), "/missing", [])
    try:
        backend.get_status("missing")
        assert False
    except ServiceNotFoundError:
        pass


def test_status_uses_process_observation(tmp_path: Path, monkeypatch):
    fake = FakeInspector([ProcessInfo(pid=123, name="demo", status="running", cmdline="demo --loop")])
    backend = _backend(tmp_path, fake)
    monkeypatch.setattr(backend, "_sv", lambda d, action: type("R", (), {"returncode": 0, "stdout": "run: demo: (pid 123) 5s", "stderr": ""})())
    info = backend.get_status("demo")
    assert info.state == ServiceState.RUNNING
    assert info.pid == 123
    assert info.extra["adapter"] == "termux-runit"


def test_mutations_use_fixed_argv(monkeypatch, tmp_path: Path):
    backend = _backend(tmp_path)
    calls = []
    monkeypatch.setattr(backend, "_sv", lambda d, action: calls.append((d.name, action)) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    monkeypatch.setattr(backend, "get_status", lambda name: type("I", (), {"name": name, "state": ServiceState.RUNNING})())
    backend.start("demo")
    backend.stop("demo")
    backend.restart("demo")
    assert calls == [("demo", "up"), ("demo", "down"), ("demo", "restart")]


def test_detection_is_noninvasive(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("PREFIX", raising=False)
    result = detect_termux(str(tmp_path))
    assert result.service_root == str(tmp_path)
    assert result.active_services == ()
