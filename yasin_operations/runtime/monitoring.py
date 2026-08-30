"""Canonical read-only monitoring snapshot for Hermes and operators.

Builds a deterministic, machine-readable view from status, health, doctor and
resource signals without performing any mutating actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from yasin_operations.core.results.models import OperationResult
from yasin_operations.runtime.resources import snapshot as resource_snapshot

# Known optional ecosystem service names (label only; registry remains config-driven).
OPTIONAL_ECOSYSTEM_SERVICES: frozenset[str] = frozenset(
    {
        "hermes-agent",
        "hermes",
        "yasin-ai",
        "yasinai",
        "yasinpress",
        "yasin-press",
        "yasinrelay",
        "yasin-relay",
        "yasin-operations",
    }
)

MONITORING_SCHEMA_VERSION = 1


def classify_service(service: Mapping[str, Any]) -> str:
    """Return a stable monitoring class for one service observation."""
    health = str(service.get("health_state") or "").lower()
    state = str(service.get("state") or "unknown").lower()
    extra = service.get("extra") or {}
    presence = str(extra.get("presence") or "").lower() if isinstance(extra, Mapping) else ""

    if health == "missing" or presence == "missing":
        return "missing"
    if health == "unavailable" or presence == "backend_unavailable":
        return "unavailable"
    if health == "failed" or state == "failed":
        return "failed"
    if state in {"running"} and health in {"ok", "healthy", ""}:
        return "healthy"
    if state in {"stopped", "degraded", "starting", "stopping"}:
        return "degraded"
    if health in {"stopped", "degraded"}:
        return "degraded"
    if state == "unknown" or health in {"unknown", ""}:
        return "unknown"
    return "other"


def is_optional_ecosystem_service(name: str) -> bool:
    return name.lower().strip() in OPTIONAL_ECOSYSTEM_SERVICES


def monitoring_summary(services: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate service observations into monitoring-oriented counts and health."""
    counts = {
        "healthy": 0,
        "degraded": 0,
        "failed": 0,
        "missing": 0,
        "unavailable": 0,
        "unknown": 0,
        "other": 0,
    }
    optional_missing: list[str] = []
    product_failures: list[str] = []
    degraded_names: list[str] = []

    for service in services:
        name = str(service.get("name") or "")
        klass = classify_service(service)
        counts[klass if klass in counts else "other"] += 1
        if klass == "missing":
            optional_missing.append(name)
        elif klass == "failed":
            product_failures.append(name)
        elif klass == "degraded":
            degraded_names.append(name)

    total = len(services)
    # Missing optional services must not force unhealthy.
    if product_failures or counts["unknown"] or counts["other"]:
        health = "unhealthy"
    elif counts["degraded"] or counts["unavailable"]:
        health = "degraded"
    elif counts["missing"] and counts["healthy"] + counts["missing"] == total:
        health = "degraded" if counts["healthy"] else "healthy"
        if counts["healthy"] == 0 and counts["missing"] == total:
            health = "healthy"
    elif counts["healthy"] == total or total == 0:
        health = "healthy"
    else:
        health = "degraded"

    return {
        "total": total,
        "counts": counts,
        "health": health,
        "optional_missing": sorted(optional_missing),
        "product_failures": sorted(product_failures),
        "degraded": sorted(degraded_names),
    }


@dataclass(frozen=True)
class MonitoringSnapshot:
    """Structured monitoring pass result."""

    schema_version: int
    success: bool
    aggregate_health: str
    services: list[dict[str, Any]]
    service_summary: dict[str, Any]
    health: dict[str, Any]
    diagnostics: dict[str, Any]
    resources: dict[str, Any]
    failures: list[dict[str, Any]]
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "command": "monitor",
            "success": self.success,
            "aggregate_health": self.aggregate_health,
            "services": {
                "items": self.services,
                "summary": self.service_summary,
            },
            "health": self.health,
            "diagnostics": self.diagnostics,
            "resources": self.resources,
            "failures": self.failures,
            "error": self.error,
        }


def _result_error(result: OperationResult) -> dict[str, Any] | None:
    if result.error is None:
        return None
    return {
        "category": result.error.category.value,
        "message": result.error.message,
        "details": dict(result.error.details),
    }


def _enrich_service(raw: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    item["classification"] = classify_service(item)
    item["optional_ecosystem"] = is_optional_ecosystem_service(str(item.get("name") or ""))
    desired = item.get("desired_state")
    observed = item.get("state")
    item["desired_matches_observed"] = (
        desired is not None and observed is not None and str(desired) == str(observed)
    )
    return item


def build_monitoring_snapshot(
    *,
    services_result: OperationResult,
    health_result: OperationResult,
    diagnostics: Mapping[str, Any] | None = None,
    diagnostics_ok: bool = True,
) -> MonitoringSnapshot:
    """Compose one read-only monitoring snapshot from Executor results + doctor data."""
    service_data = dict(services_result.data or {})
    raw_services = list(service_data.get("services") or [])
    services = [_enrich_service(s) for s in raw_services]
    summary = monitoring_summary(services)
    health = dict(health_result.data or {})
    diagnostics_data = dict(diagnostics or {})
    resources = resource_snapshot().as_dict()

    failures: list[dict[str, Any]] = []
    for service in services:
        if service["classification"] in {"failed", "unavailable"}:
            failures.append(
                {
                    "name": service.get("name"),
                    "classification": service["classification"],
                    "state": service.get("state"),
                    "health_state": service.get("health_state"),
                    "message": service.get("message"),
                    "desired_state": service.get("desired_state"),
                }
            )

    success = services_result.success and health_result.success and diagnostics_ok
    runtime_status = str(health.get("status") or "unknown").lower()
    if not success or runtime_status in {"unhealthy", "timeout"} or summary["health"] == "unhealthy":
        aggregate = "unhealthy"
    elif runtime_status in {"degraded", "unknown"} or summary["health"] == "degraded":
        aggregate = "degraded"
    else:
        aggregate = "healthy"

    error = _result_error(services_result) or _result_error(health_result)
    if error is None and not diagnostics_ok:
        error = {
            "category": "diagnostics",
            "message": "one or more diagnostics reported issues",
            "details": {},
        }

    return MonitoringSnapshot(
        schema_version=MONITORING_SCHEMA_VERSION,
        success=success,
        aggregate_health=aggregate,
        services=services,
        service_summary=summary,
        health=health,
        diagnostics=diagnostics_data,
        resources=resources,
        failures=failures,
        error=error,
    )
