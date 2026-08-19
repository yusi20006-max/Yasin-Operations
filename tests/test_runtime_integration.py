"""End-to-end Runtime + Core Executor integration and independence."""

from __future__ import annotations

import os

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.runtime.tools import register_runtime_tools
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.registry.registry import ToolRegistry


def test_runtime_tools_through_executor():
    registry = ToolRegistry()
    register_runtime_tools(registry)
    executor = Executor(registry)

    result = executor.execute(
        Operation(
            name="list_processes",
            target=OperationTarget(kind="process", identifier="*"),
            safety_class=SafetyClass.READ_ONLY,
        )
    )
    assert result.success
    assert "processes" in result.data
    assert any(p["pid"] == os.getpid() for p in result.data["processes"])

    result2 = executor.execute(
        Operation(
            name="process_status",
            target=OperationTarget(kind="process", identifier=str(os.getpid())),
            safety_class=SafetyClass.READ_ONLY,
            parameters={"pid": os.getpid()},
        )
    )
    assert result2.success
    assert result2.data["pid"] == os.getpid()

    result3 = executor.execute(
        Operation(
            name="health_check",
            target=OperationTarget(kind="self", identifier="runtime"),
            safety_class=SafetyClass.READ_ONLY,
        )
    )
    assert result3.success
    assert result3.data["status"] == "healthy"

    result4 = executor.execute(
        Operation(
            name="diagnostics",
            target=OperationTarget(kind="runtime", identifier="local"),
            safety_class=SafetyClass.READ_ONLY,
        )
    )
    assert result4.success
    assert result4.data["python_version"]
    assert "runtime.process" in result4.data["registered_tools"]


def test_independence_no_external_yasin_imports():
    """Runtime modules must not import other Yasin projects."""
    import yasin_operations.runtime as rt
    import yasin_operations.runtime.tools as tools
    import yasin_operations.runtime.local.process_backend as pb
    import yasin_operations.runtime.local.service_backend as sb

    forbidden = ("hermes", "yasin_ai", "yasinpress", "yasinrelay", "yasin_press", "yasin_relay")
    for mod in (rt, tools, pb, sb):
        for name in dir(mod):
            assert not any(f in name.lower() for f in forbidden)
        path = getattr(mod, "__file__", None)
        if path and path.endswith(".py"):
            text = open(path, encoding="utf-8").read().lower()
            for f in forbidden:
                assert f"import {f}" not in text
                assert f"from {f}" not in text
