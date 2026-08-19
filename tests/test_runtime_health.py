"""Health-check tests (Runtime Issue #2)."""

from __future__ import annotations

from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory
from yasin_operations.runtime.health import HealthStatus
from yasin_operations.runtime.local.service_backend import (
    LocalServiceBackend,
    ServiceDefinition,
)
from yasin_operations.runtime.process import InvalidPIDError, ProcessInfo, ProcessNotFoundError
from yasin_operations.runtime.service import ServiceState
from yasin_operations.runtime.tools import HealthTool
from yasin_operations.safety.classification import SafetyClass


class FakeInspector:
    def __init__(self, alive_pids: set[int] | None = None):
        self.alive_pids = alive_pids or set()

    def list_processes(self):
        return [
            ProcessInfo(pid=p, name="x", status="running") for p in self.alive_pids
        ]

    def get_process(self, pid: int) -> ProcessInfo:
        if pid <= 0:
            raise InvalidPIDError(pid)
        if pid not in self.alive_pids:
            raise ProcessNotFoundError(str(pid))
        return ProcessInfo(pid=pid, name="x", status="running")

    def find_by_name(self, pattern: str):
        return []

    def is_alive(self, pid: int) -> bool:
        return pid in self.alive_pids


def test_healthy_process():
    tool = HealthTool(FakeInspector({100}))
    op = Operation(
        name="health_check",
        target=OperationTarget(kind="process", identifier="100"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    assert result.data["status"] == HealthStatus.HEALTHY.value
    assert result.data["latency_ms"] is not None


def test_unhealthy_process():
    tool = HealthTool(FakeInspector(set()))
    op = Operation(
        name="health_check",
        target=OperationTarget(kind="process", identifier="100"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    assert result.data["status"] == HealthStatus.UNHEALTHY.value
    assert result.data["failure_reason"]


def test_self_health():
    tool = HealthTool(FakeInspector())
    op = Operation(
        name="health_check",
        target=OperationTarget(kind="self", identifier="runtime"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    assert result.data["status"] == HealthStatus.HEALTHY.value


def test_service_health_running():
    inspector = FakeInspector({50})
    backend = LocalServiceBackend(
        inspector,
        definitions=[
            ServiceDefinition(name="svc", process_pattern="svc"),
        ],
    )
    inspector.find_by_name = lambda p: [  # type: ignore[method-assign]
        ProcessInfo(pid=50, name="svc", status="running", cmdline="svc")
    ]
    tool = HealthTool(inspector, backend)
    op = Operation(
        name="health_check",
        target=OperationTarget(kind="service", identifier="svc"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    assert result.data["status"] == HealthStatus.HEALTHY.value
    assert "diagnostic" in result.data


def test_service_health_not_found():
    backend = LocalServiceBackend(FakeInspector(), definitions=[])
    tool = HealthTool(FakeInspector(), backend)
    op = Operation(
        name="health_check",
        target=OperationTarget(kind="service", identifier="missing"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    assert result.data["status"] == HealthStatus.UNHEALTHY.value


def test_structured_diagnostic_output():
    tool = HealthTool(FakeInspector({1}))
    op = Operation(
        name="health_check",
        target=OperationTarget(kind="process", identifier="1"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    data = result.data
    for key in ("target", "status", "timestamp", "latency_ms", "diagnostic"):
        assert key in data
