"""Production diagnostics coverage for Issue #33."""
from __future__ import annotations

import json
from pathlib import Path

from yasin_operations.runtime.termux.diagnostics import detect_termux


def _termux_env() -> dict[str, str]:
    return {"PREFIX": "/data/data/com.termux/files/usr"}


def _sv(tmp_path: Path, executable: bool = True) -> Path:
    path = tmp_path / "bin" / "sv"
    path.parent.mkdir()
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)
    return path


def test_healthy_termux_snapshot_is_complete(tmp_path: Path) -> None:
    root = tmp_path / "service"
    root.mkdir()
    (root / "demo").mkdir()
    sv = _sv(tmp_path)

    result = detect_termux(
        str(root),
        sv_path=str(sv),
        expected_services=("demo",),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "missing-marker"),
    )

    assert result.status == "healthy"
    assert result.runit_available
    assert result.service_root_exists
    assert result.service_root_readable
    assert result.sv_exists
    assert result.sv_executable
    assert result.active_services == ("demo",)
    assert result.configured_services == ("demo",)
    assert result.missing_services == ()
    assert result.issues == ()
    payload = result.as_dict()
    assert payload["status"] == "healthy"
    assert json.dumps(payload, sort_keys=True)


def test_missing_runtime_components_are_actionable(tmp_path: Path) -> None:
    result = detect_termux(
        str(tmp_path / "missing-service-root"),
        sv_path=str(tmp_path / "missing-sv"),
        expected_services=("demo", "yasin-ai"),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "missing-marker"),
    )

    assert result.status == "degraded"
    assert not result.runit_available
    assert not result.service_root_exists
    assert not result.sv_exists
    assert "service_root_missing" in result.issues
    assert "runit_sv_missing" in result.issues
    assert result.missing_services == ("demo", "yasin-ai")


def test_missing_configured_service_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "service"
    root.mkdir()
    (root / "demo").mkdir()
    sv = _sv(tmp_path)

    result = detect_termux(
        str(root),
        sv_path=str(sv),
        expected_services=("demo", "missing"),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "missing-marker"),
    )

    assert result.missing_services == ("missing",)
    assert "service_missing:missing" in result.issues


def test_non_executable_sv_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "service"
    root.mkdir()
    sv = _sv(tmp_path, executable=False)

    result = detect_termux(
        str(root),
        sv_path=str(sv),
        environ=_termux_env(),
        termux_marker=str(tmp_path / "missing-marker"),
    )

    assert result.status == "degraded"
    assert result.sv_exists
    assert not result.sv_executable
    assert not result.runit_available
    assert "runit_sv_not_executable" in result.issues


def test_non_termux_is_explicitly_unsupported_and_has_no_false_positive(tmp_path: Path) -> None:
    root = tmp_path / "service"
    root.mkdir()

    result = detect_termux(
        str(root),
        sv_path=str(tmp_path / "missing-sv"),
        expected_services=("demo",),
        environ={},
        termux_marker=str(tmp_path / "missing-marker"),
    )

    assert result.status == "unsupported"
    assert not result.is_termux
    assert result.issues == ()
    assert result.missing_services == ()
