"""Issue #3 Termux/runit adapter tests."""
from __future__ import annotations

from pathlib import Path

from yasin_operations.runtime.process import ProcessInfo
from yasin_operations.runtime.service import ServiceState, ServiceNotFoundError
from yasin_operations.runtime.termux.diagnostics import detect_termux
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition, _normalize_runit_status


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
    assert info.health_state == "ok"
    assert info.extra["adapter"] == "termux-runit"


def test_runit_run_status_is_running():
    assert _normalize_runit_status("run: yasin-ai: (pid 123) 42s", 0) == ServiceState.RUNNING


def test_runit_down_status_is_stopped_even_with_zero_exit_code():
    assert _normalize_runit_status("down: yasinpress: normally up", 0) == ServiceState.STOPPED


def test_runit_fail_and_timeout_are_failed():
    assert _normalize_runit_status("fail: yasinpress: unable to open supervise/ok", 0) == ServiceState.FAILED
    assert _normalize_runit_status("timeout: yasinpress: 5s", 0) == ServiceState.FAILED


def test_unknown_runit_status_is_unknown():
    assert _normalize_runit_status("unexpected status output", 0) == ServiceState.UNKNOWN
    assert _normalize_runit_status("", 1) == ServiceState.UNKNOWN


def test_down_service_is_not_healthy_or_running(tmp_path: Path, monkeypatch):
    fake = FakeInspector([ProcessInfo(pid=123, name="demo", status="running", cmdline="demo --loop")])
    backend = _backend(tmp_path, fake)
    monkeypatch.setattr(backend, "_sv", lambda d, action: type("R", (), {"returncode": 0, "stdout": "down: demo: normally up", "stderr": ""})())
    info = backend.get_status("demo")
    assert info.state == ServiceState.STOPPED
    assert info.health_state == "stopped"
    assert info.pid is None
    assert info.desired_state == ServiceState.RUNNING


def test_mixed_services_preserve_actual_state(tmp_path: Path, monkeypatch):
    service_root = tmp_path / "service"
    service_root.mkdir()
    (service_root / "healthy").mkdir()
    (service_root / "down").mkdir()
    sv = tmp_path / "sv"
    sv.write_text("#!/bin/sh\n", encoding="utf-8")
    sv.chmod(0o755)
    inspector = FakeInspector([
        ProcessInfo(pid=10, name="healthy", status="running", cmdline="healthy --loop"),
        ProcessInfo(pid=20, name="down", status="running", cmdline="down --stale"),
    ])
    backend = RunitServiceBackend(
        inspector,
        str(service_root),
        [
            RunitServiceDefinition("healthy", process_pattern="healthy"),
            RunitServiceDefinition("down", process_pattern="down"),
        ],
        sv_path=str(sv),
    )

    def fake_sv(definition, action):
        output = "run: healthy: (pid 10) 5s" if definition.name == "healthy" else "down: down: normally up"
        return type("R", (), {"returncode": 0, "stdout": output, "stderr": ""})()

    monkeypatch.setattr(backend, "_sv", fake_sv)
    infos = backend.list_services()
    assert [(i.name, i.state, i.health_state) for i in infos] == [
        ("down", ServiceState.STOPPED, "stopped"),
        ("healthy", ServiceState.RUNNING, "ok"),
    ]


def test_status_returncode_does_not_override_authoritative_prefix(tmp_path: Path, monkeypatch):
    backend = _backend(tmp_path)
    monkeypatch.setattr(backend, "_sv", lambda d, action: type("R", (), {"returncode": 1, "stdout": "run: demo: (pid 123) 5s", "stderr": "warning"})())
    info = backend.get_status("demo")
    assert info.state == ServiceState.RUNNING
    assert info.health_state == "ok"


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
