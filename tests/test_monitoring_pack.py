"""P4.3 monitoring pack contract tests."""
from __future__ import annotations

from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.runtime.monitoring import (
    build_monitoring_snapshot,
    classify_service,
    is_optional_ecosystem_service,
    monitoring_summary,
)


def test_classify_missing_optional_service() -> None:
    assert (
        classify_service(
            {
                "name": "hermes-agent",
                "state": "unknown",
                "health_state": "missing",
                "extra": {"presence": "missing"},
            }
        )
        == "missing"
    )
    assert is_optional_ecosystem_service("hermes-agent")
    assert is_optional_ecosystem_service("yasinpress")


def test_classify_failed_and_healthy() -> None:
    assert classify_service({"name": "a", "state": "failed", "health_state": "failed"}) == "failed"
    assert classify_service({"name": "b", "state": "running", "health_state": "ok"}) == "healthy"
    assert classify_service({"name": "c", "state": "stopped", "health_state": "stopped"}) == "degraded"


def test_monitoring_summary_missing_optional_is_not_unhealthy() -> None:
    services = [
        {
            "name": "hermes-agent",
            "state": "unknown",
            "health_state": "missing",
            "extra": {"presence": "missing"},
        },
        {
            "name": "yasinpress",
            "state": "unknown",
            "health_state": "missing",
            "extra": {"presence": "missing"},
        },
    ]
    summary = monitoring_summary(services)
    assert summary["counts"]["missing"] == 2
    assert summary["health"] == "healthy"
    assert summary["product_failures"] == []
    assert "hermes-agent" in summary["optional_missing"]


def test_monitoring_summary_mixed_healthy_degraded_failed() -> None:
    services = [
        {"name": "a", "state": "running", "health_state": "ok"},
        {"name": "b", "state": "stopped", "health_state": "stopped"},
        {"name": "c", "state": "failed", "health_state": "failed"},
        {
            "name": "yasin-ai",
            "state": "unknown",
            "health_state": "missing",
            "extra": {"presence": "missing"},
        },
    ]
    summary = monitoring_summary(services)
    assert summary["counts"]["healthy"] == 1
    assert summary["counts"]["degraded"] == 1
    assert summary["counts"]["failed"] == 1
    assert summary["counts"]["missing"] == 1
    assert summary["health"] == "unhealthy"
    assert summary["product_failures"] == ["c"]
    assert "yasin-ai" in summary["optional_missing"]


def test_build_monitoring_snapshot_read_only_contract() -> None:
    services_result = OperationResult.ok(
        "svc-1",
        {
            "services": [
                {
                    "name": "demo",
                    "state": "running",
                    "desired_state": "running",
                    "health_state": "ok",
                    "extra": {"presence": "present"},
                },
                {
                    "name": "hermes-agent",
                    "state": "unknown",
                    "desired_state": "running",
                    "health_state": "missing",
                    "extra": {"presence": "missing"},
                },
            ]
        },
    )
    health_result = OperationResult.ok("health-1", {"status": "healthy", "checks": []})
    snapshot = build_monitoring_snapshot(
        services_result=services_result,
        health_result=health_result,
        diagnostics={"termux": {"available": False}, "configuration": {}},
        diagnostics_ok=True,
    )
    payload = snapshot.as_dict()
    assert payload["schema_version"] == 1
    assert payload["command"] == "monitor"
    assert payload["success"] is True
    assert payload["aggregate_health"] in {"healthy", "degraded"}
    assert len(payload["services"]["items"]) == 2
    classifications = {item["name"]: item["classification"] for item in payload["services"]["items"]}
    assert classifications["demo"] == "healthy"
    assert classifications["hermes-agent"] == "missing"
    assert payload["services"]["items"][0]["desired_matches_observed"] is True
    assert "resources" in payload
    assert payload["failures"] == []


def test_build_monitoring_snapshot_surfaces_product_failures() -> None:
    services_result = OperationResult.ok(
        "svc-2",
        {
            "services": [
                {
                    "name": "broken",
                    "state": "failed",
                    "desired_state": "running",
                    "health_state": "failed",
                    "message": "sv failed",
                    "extra": {"presence": "present"},
                }
            ]
        },
    )
    health_result = OperationResult.ok("health-2", {"status": "healthy"})
    snapshot = build_monitoring_snapshot(
        services_result=services_result,
        health_result=health_result,
        diagnostics={},
        diagnostics_ok=True,
    )
    assert snapshot.aggregate_health == "unhealthy"
    assert snapshot.failures[0]["name"] == "broken"


def test_build_monitoring_snapshot_propagates_executor_error() -> None:
    services_result = OperationResult.fail(
        "svc-3",
        OperationError(ErrorCategory.UNAVAILABLE_DEPENDENCY, "backend down"),
    )
    health_result = OperationResult.ok("health-3", {"status": "healthy"})
    snapshot = build_monitoring_snapshot(
        services_result=services_result,
        health_result=health_result,
        diagnostics={},
        diagnostics_ok=True,
    )
    assert snapshot.success is False
    assert snapshot.error is not None
    assert snapshot.error["category"] == "unavailable_dependency"
