"""Diagnostics tests (Runtime Issue #2)."""

from __future__ import annotations

from yasin_operations.config.config import OperationsConfig
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.runtime.local.service_backend import (
    LocalServiceBackend,
    ServiceDefinition,
)
from yasin_operations.runtime.process import ProcessInfo
from yasin_operations.runtime.tools import DiagnosticsTool, ProcessTool, register_runtime_tools
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.registry.registry import ToolRegistry


class FakeInspector:
    def list_processes(self):
        return []

    def get_process(self, pid: int) -> ProcessInfo:
        return ProcessInfo(pid=pid, name="pytest", status="running", memory_rss_bytes=1024)

    def find_by_name(self, pattern: str):
        return []

    def is_alive(self, pid: int) -> bool:
        return True


def test_diagnostics_snapshot_structure():
    registry = ToolRegistry()
    backend = LocalServiceBackend(
        FakeInspector(),
        definitions=[ServiceDefinition(name="demo", process_pattern="demo")],
    )
    tool = DiagnosticsTool(
        registry=registry,
        service_backend=backend,
        config=OperationsConfig(),
        inspector=FakeInspector(),
    )
    registry.register(ProcessTool(FakeInspector()))
    registry.register(tool)

    op = Operation(
        name="diagnostics",
        target=OperationTarget(kind="runtime", identifier="local"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = tool.execute(op)
    assert result.success
    data = result.data
    assert "python_version" in data
    assert "platform" in data
    assert "os_name" in data
    assert "process" in data
    assert "registered_tools" in data
    assert "configuration" in data
    assert "services" in data
    assert "execution_timeout_seconds" in data["configuration"]
    assert "log_level" in data["configuration"]
    assert "environ" not in data
    assert "env" not in data
    assert any("runtime.process" in t for t in data["registered_tools"])


def test_register_runtime_tools():
    registry = ToolRegistry()
    register_runtime_tools(registry, inspector=FakeInspector())
    ids = {d.id for d in registry.list_tools()}
    assert "runtime.process" in ids
    assert "runtime.service" in ids
    assert "runtime.health" in ids
    assert "runtime.diagnostics" in ids
