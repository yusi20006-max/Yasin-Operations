"""P4.4 Termux/runit live acceptance contract tests."""
from __future__ import annotations

import stat
import subprocess
from pathlib import Path

from yasin_operations.runtime.termux.live_acceptance import (
    DEFAULT_OPTIONAL_SERVICES,
    evaluate_live_services,
)


def _make_sv(tmp_path: Path, script: str = "#!/bin/sh\necho 'run: demo: (pid 1) 1s'\nexit 0\n") -> Path:
    sv = tmp_path / "sv"
    sv.write_text(script, encoding="utf-8")
    sv.chmod(sv.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return sv


def _termux_env() -> dict[str, str]:
    return {"PREFIX": "/data/data/com.termux/files/usr"}


def test_missing_optional_services_are_skip_not_fail(tmp_path: Path) -> None:
    root = tmp_path / "service"
    root.mkdir()
    sv = _make_sv(tmp_path)
    report = evaluate_live_services(
        ("hermes-agent", "yasinpress"),
        service_root=str(root),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    by_name = {item.name: item for item in report.results}
    assert by_name["service:hermes-agent"].status == "SKIP"
    assert by_name["service:yasinpress"].status == "SKIP"
    assert by_name["service:hermes-agent"].category == "optional"
    assert report.success is True
    assert report.summary()["fail"] == 0


def test_running_service_passes(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "service"
    root.mkdir()
    (root / "yasinpress").mkdir()
    sv = _make_sv(tmp_path)

    completed = subprocess.CompletedProcess(
        [str(sv), "status", str(root / "yasinpress")],
        0,
        "run: yasinpress: (pid 42) 3s",
        "",
    )
    monkeypatch.setattr(
        "yasin_operations.runtime.termux.runit.subprocess.run",
        lambda *args, **kwargs: completed,
    )
    monkeypatch.setattr("yasin_operations.runtime.termux.runit.os.access", lambda path, mode: True)

    report = evaluate_live_services(
        ("yasinpress",),
        service_root=str(root),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    by_name = {item.name: item for item in report.results}
    assert by_name["service:yasinpress"].status == "PASS"
    assert by_name["service:yasinpress"].state == "running"
    assert report.success is True


def test_down_service_is_product_fail_not_false_healthy(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "service"
    root.mkdir()
    (root / "yasin-ai").mkdir()
    sv = _make_sv(tmp_path)
    completed = subprocess.CompletedProcess(
        [str(sv), "status", str(root / "yasin-ai")],
        0,
        "down: yasin-ai: 4s, normally up",
        "",
    )
    monkeypatch.setattr(
        "yasin_operations.runtime.termux.runit.subprocess.run",
        lambda *args, **kwargs: completed,
    )
    monkeypatch.setattr("yasin_operations.runtime.termux.runit.os.access", lambda path, mode: True)

    report = evaluate_live_services(
        ("yasin-ai",),
        service_root=str(root),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    item = next(r for r in report.results if r.name == "service:yasin-ai")
    assert item.status == "FAIL"
    assert item.category == "product"
    assert item.state == "stopped"
    assert report.success is False


def test_mixed_missing_and_failed_isolation(tmp_path: Path, monkeypatch) -> None:
    """One failed service must not hide missing/optional observations."""
    root = tmp_path / "service"
    root.mkdir()
    (root / "yasinpress").mkdir()
    # hermes-agent directory absent
    sv = _make_sv(tmp_path)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            "fail: yasinpress: 1s, normally up",
            "",
        )

    monkeypatch.setattr("yasin_operations.runtime.termux.runit.subprocess.run", fake_run)
    monkeypatch.setattr("yasin_operations.runtime.termux.runit.os.access", lambda path, mode: True)

    report = evaluate_live_services(
        ("hermes-agent", "yasinpress"),
        service_root=str(root),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    by_name = {item.name: item for item in report.results}
    assert by_name["service:hermes-agent"].status == "SKIP"
    assert by_name["service:yasinpress"].status == "FAIL"
    assert by_name["service:yasinpress"].state == "failed"
    assert report.summary()["skip"] >= 1
    assert report.summary()["fail"] >= 1


def test_missing_service_root_is_environment_blocked(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-root"
    sv = _make_sv(tmp_path)
    report = evaluate_live_services(
        ("hermes-agent",),
        service_root=str(missing),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    assert report.environment_blocked is True
    assert any(item.status == "BLOCKED" and item.category == "environment" for item in report.results)
    assert report.success is False


def test_unavailable_sv_is_environment_blocked(tmp_path: Path) -> None:
    root = tmp_path / "service"
    root.mkdir()
    (root / "yasinpress").mkdir()
    report = evaluate_live_services(
        ("yasinpress", "hermes-agent"),
        service_root=str(root),
        sv_path=str(tmp_path / "missing-sv"),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    assert report.environment_blocked is True
    assert any(item.name == "environment:sv" and item.status == "BLOCKED" for item in report.results)
    # Missing optional still reported without sv.
    assert any(item.name == "service:hermes-agent" and item.status == "SKIP" for item in report.results)


def test_default_optional_service_set() -> None:
    assert "hermes-agent" in DEFAULT_OPTIONAL_SERVICES
    assert "yasin-ai" in DEFAULT_OPTIONAL_SERVICES
    assert "yasinpress" in DEFAULT_OPTIONAL_SERVICES
    assert "yasinrelay" in DEFAULT_OPTIONAL_SERVICES


def test_service_directory_drift_is_observation(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "service"
    root.mkdir()
    (root / "yasinpress").mkdir()
    (root / "extra-service").mkdir()
    sv = _make_sv(tmp_path)
    completed = subprocess.CompletedProcess([str(sv), "status"], 0, "run: yasinpress: (pid 1) 1s", "")
    monkeypatch.setattr(
        "yasin_operations.runtime.termux.runit.subprocess.run",
        lambda *args, **kwargs: completed,
    )
    monkeypatch.setattr("yasin_operations.runtime.termux.runit.os.access", lambda path, mode: True)

    report = evaluate_live_services(
        ("yasinpress",),
        service_root=str(root),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "no-marker"),
    )
    assert any(
        item.name == "observation:service_directory_drift" and "extra-service" in item.detail
        for item in report.results
    )
