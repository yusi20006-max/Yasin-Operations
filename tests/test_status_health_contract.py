from __future__ import annotations

import json

import pytest

from yasin_operations.cli import (
    HEALTH_EXIT_DEGRADED,
    HEALTH_EXIT_OK,
    HEALTH_EXIT_UNHEALTHY,
    STATUS_EXIT_DEGRADED,
    STATUS_EXIT_ERROR,
    STATUS_EXIT_OK,
    _health_exit_code,
    _service_summary,
)
from yasin_operations.runtime import resources


def test_service_summary_classifies_running_services_as_healthy() -> None:
    result = _service_summary([
        {"name": "a", "state": "running"},
        {"name": "b", "state": "running"},
    ])
    assert result["health"] == "healthy"
    assert result["exit_code"] == STATUS_EXIT_OK
    assert result["counts"]["running"] == 2


def test_service_summary_classifies_stopped_or_degraded_as_degraded() -> None:
    result = _service_summary([
        {"name": "a", "state": "running"},
        {"name": "b", "state": "stopped"},
        {"name": "c", "state": "degraded"},
    ])
    assert result["health"] == "degraded"
    assert result["exit_code"] == STATUS_EXIT_DEGRADED
    assert result["counts"]["stopped"] == 1
    assert result["counts"]["degraded"] == 1


def test_service_summary_classifies_failed_or_unknown_as_unhealthy() -> None:
    result = _service_summary([
        {"name": "a", "state": "failed"},
        {"name": "b", "state": "unknown"},
    ])
    assert result["health"] == "unhealthy"
    assert result["exit_code"] == STATUS_EXIT_ERROR


@pytest.mark.parametrize(
    ("health", "service_health", "expected"),
    [
        ({"status": "healthy"}, "healthy", HEALTH_EXIT_OK),
        ({"status": "healthy"}, "degraded", HEALTH_EXIT_DEGRADED),
        ({"status": "degraded"}, "healthy", HEALTH_EXIT_DEGRADED),
        ({"status": "unknown"}, "healthy", HEALTH_EXIT_DEGRADED),
        ({"status": "timeout"}, "healthy", HEALTH_EXIT_UNHEALTHY),
        ({"status": "healthy"}, "unhealthy", HEALTH_EXIT_UNHEALTHY),
    ],
)
def test_health_exit_code_is_deterministic(health: dict, service_health: str, expected: int) -> None:
    summary = {"health": service_health}
    assert _health_exit_code(health, summary) == expected


def test_resource_snapshot_survives_unavailable_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resources.resource, "getrusage", lambda *_args: (_ for _ in ()).throw(OSError("unavailable")))
    monkeypatch.setattr(resources.os, "getloadavg", lambda: (_ for _ in ()).throw(OSError("unavailable")))
    result = resources.snapshot().as_dict()
    assert result["rss_bytes"] is None
    assert result["user_cpu_seconds"] == 0.0
    assert result["system_cpu_seconds"] == 0.0
    assert result["load_average_1m"] is None
    json.dumps(result)
