from __future__ import annotations

from pathlib import Path

from scripts.production_acceptance import _service_root


def test_termux_service_root_defaults_to_prefix_when_configured(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_ROOT", str(tmp_path / "services"))
    assert _service_root() == tmp_path / "services"


def test_termux_service_root_expands_user_home(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("YASIN_OPERATIONS_SERVICE_ROOT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_ROOT", "~/services")
    assert _service_root() == tmp_path / "services"
