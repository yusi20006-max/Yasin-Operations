from pathlib import Path

import pytest

from yasin_operations import termux_launcher as launcher


@pytest.fixture
def spec():
    return launcher.LauncherSpec(
        name="demo",
        command=("demo",),
        port=7777,
        identity="demo-service",
        lifecycle="direct",
    )


def test_free_port_starts_and_verifies(monkeypatch, spec):
    calls = []
    monkeypatch.setattr(launcher, "_pids_for_port", lambda port: [])
    monkeypatch.setattr(launcher, "port_is_free", lambda port: len(calls) == 0)
    monkeypatch.setattr(launcher, "_run", lambda command, cwd=None: calls.append(command) or type("R", (), {"returncode": 0})())
    assert launcher.launch(spec, ["--x"]) == 0
    assert calls == [("demo", "--x")]


def test_foreign_owner_fails_closed(monkeypatch, spec):
    monkeypatch.setattr(launcher, "_pids_for_port", lambda port: [1234])
    monkeypatch.setattr(launcher, "port_is_free", lambda port: False)
    monkeypatch.setattr(launcher, "process_identity", lambda pid: "foreign-program")
    with pytest.raises(launcher.LauncherError, match="refusing startup"):
        launcher.launch(spec, [])


def test_unknown_owner_fails_closed_when_pid_discovery_unavailable(monkeypatch, spec):
    monkeypatch.setattr(launcher, "_pids_for_port", lambda port: [])
    monkeypatch.setattr(launcher, "port_is_free", lambda port: False)
    with pytest.raises(launcher.LauncherError, match="owner cannot be identified"):
        launcher.launch(spec, [])


def test_same_owner_gracefully_stops_then_starts(monkeypatch, spec):
    calls = []
    monkeypatch.setattr(launcher, "_pids_for_port", lambda port: [1234] if not calls else [])
    monkeypatch.setattr(launcher, "port_is_free", lambda port: bool(calls))
    monkeypatch.setattr(launcher, "process_identity", lambda pid: "python demo-service")
    monkeypatch.setattr(launcher, "_wait_until", lambda predicate, timeout=8.0: True)
    monkeypatch.setattr(launcher, "_run", lambda command, cwd=None: calls.append(command) or type("R", (), {"returncode": 0})())
    assert launcher.launch(spec, []) == 0
    assert calls == [("demo",)]


def test_portless_forwards_arguments(monkeypatch):
    spec = launcher.LauncherSpec(name="opencode", command=("opencode",))
    calls = []
    monkeypatch.setattr(launcher, "_run", lambda command, cwd=None: calls.append(command) or type("R", (), {"returncode": 0})())
    assert launcher.launch(spec, ["--help"]) == 0
    assert calls == [("opencode", "--help")]


def test_hub_managed_occupied_port_delegates_restart(monkeypatch):
    spec = launcher.LauncherSpec(name="yasin-agent", command=("yasin", "start", "yasin-agent"), port=7002, lifecycle="hub")
    monkeypatch.setattr(launcher, "port_is_free", lambda port: False)
    calls = []
    monkeypatch.setattr(launcher, "_run", lambda command, cwd=None: calls.append(command) or type("R", (), {"returncode": 0})())
    assert launcher.launch(spec, []) == 0
    assert calls == [("yasin", "restart", "yasin-agent")]
