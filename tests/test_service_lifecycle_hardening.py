"""Regression coverage for hardened service lifecycle behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from yasin_operations.runtime.service import ServiceCommandError, ServiceNotFoundError, ServiceTimeoutError
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition


class Inspector:
    def find_by_name(self, pattern: str):
        return []


def backend(tmp_path: Path) -> RunitServiceBackend:
    root = tmp_path / "service"
    root.mkdir()
    (root / "demo").mkdir()
    sv = tmp_path / "sv"
    sv.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    sv.chmod(0o755)
    return RunitServiceBackend(Inspector(), str(root), [RunitServiceDefinition("demo")], sv_path=str(sv))


def test_command_failure_is_not_reported_as_success(tmp_path: Path):
    service = backend(tmp_path)
    with pytest.raises(ServiceCommandError) as exc:
        service.start("demo")
    assert exc.value.name == "demo"
    assert exc.value.action == "up"
    assert exc.value.returncode == 1


def test_missing_service_directory_is_rejected(tmp_path: Path):
    root = tmp_path / "service"
    root.mkdir()
    sv = tmp_path / "sv"
    sv.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    sv.chmod(0o755)
    service = RunitServiceBackend(Inspector(), str(root), [RunitServiceDefinition("demo")], sv_path=str(sv))
    with pytest.raises(ServiceNotFoundError):
        service.restart("demo")


def test_unavailable_adapter_never_reports_a_mutation_success(tmp_path: Path):
    service = RunitServiceBackend(
        Inspector(),
        str(tmp_path),
        [RunitServiceDefinition("demo")],
        timeout=0.05,
        sv_path=str(tmp_path / "missing"),
    )
    with pytest.raises(ServiceTimeoutError):
        service.stop("demo")
