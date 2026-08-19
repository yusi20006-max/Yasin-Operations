"""Safety classification tests for Runtime Operations (Issue #2)."""

from __future__ import annotations

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory
from yasin_operations.runtime.tools import (
    DiagnosticsTool,
    HealthTool,
    ProcessTool,
    ServiceTool,
    register_runtime_tools,
)
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.registry.registry import ToolRegistry


READ_ONLY_OPS = {
    "list_processes",
    "find_process",
    "process_status",
    "process_alive",
    "service_status",
    "list_services",
    "health_check",
    "diagnostics",
}

MUTATING_OPS = {
    "service_start",
    "service_stop",
    "service_restart",
}


def _all_capabilities():
    registry = ToolRegistry()
    register_runtime_tools(registry)
    caps = {}
    for desc in registry.list_tools():
        for c in desc.capabilities:
            caps[c.operation_name] = c.safety_class
    return caps


def test_all_read_ops_are_read_only():
    caps = _all_capabilities()
    for name in READ_ONLY_OPS:
        assert name in caps, f"missing capability for {name}"
        assert caps[name] == SafetyClass.READ_ONLY, f"{name} must be READ_ONLY"


def test_all_mutating_ops_are_mutating():
    caps = _all_capabilities()
    for name in MUTATING_OPS:
        assert name in caps, f"missing capability for {name}"
        assert caps[name] == SafetyClass.MUTATING, f"{name} must be MUTATING"


def test_no_operation_bypasses_declared_safety_class():
    """Executor rejects mismatched safety_class before tool runs."""
    registry = ToolRegistry()
    register_runtime_tools(registry)
    executor = Executor(registry)

    op = Operation(
        name="service_start",
        target=OperationTarget(kind="service", identifier="x"),
        safety_class=SafetyClass.READ_ONLY,
    )
    result = executor.execute(op)
    assert not result.success
    assert result.error.category == ErrorCategory.VALIDATION_ERROR
    assert "safety_class" in result.error.message

    op2 = Operation(
        name="list_processes",
        target=OperationTarget(kind="process", identifier="*"),
        safety_class=SafetyClass.MUTATING,
    )
    result2 = executor.execute(op2)
    assert not result2.success
    assert result2.error.category == ErrorCategory.VALIDATION_ERROR


def test_tool_descriptors_cover_expected_ops():
    caps = _all_capabilities()
    expected = READ_ONLY_OPS | MUTATING_OPS
    assert expected <= set(caps.keys())
