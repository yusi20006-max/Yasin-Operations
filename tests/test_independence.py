"""Repository independence and dependency-boundary tests."""
from __future__ import annotations

import ast
import pathlib

from yasin_operations.config.config import OperationsConfig, load_config
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationState, OperationStatus, OperationTarget
from yasin_operations.core.results.models import OperationResult
from yasin_operations.logging.audit import AuditRecord, InMemoryAuditRecorder
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class _EchoTool:
    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="echo",
            description="returns its input parameters as output",
            capabilities=(ToolCapability("echo", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        return OperationResult.ok(operation.id, data=dict(operation.parameters))


def test_full_independent_flow():
    config = load_config()
    assert isinstance(config, OperationsConfig)
    registry = ToolRegistry()
    registry.register(_EchoTool())
    recorder = InMemoryAuditRecorder()
    executor = Executor(registry, audit_recorder=recorder)
    operation = Operation(
        name="echo",
        target=OperationTarget(kind="tool", identifier="echo"),
        safety_class=SafetyClass.READ_ONLY,
        parameters={"message": "hello"},
    )
    state = OperationState(operation_id=operation.id).transition_to(OperationStatus.RUNNING)
    result = executor.execute(operation)
    state = state.transition_to(OperationStatus.SUCCEEDED if result.success else OperationStatus.FAILED)
    assert result.success is True
    assert result.data == {"message": "hello"}
    assert state.status == OperationStatus.SUCCEEDED
    assert len(recorder.entries) == 1


def test_no_import_of_external_yasin_packages():
    """Internal adapter modules are allowed; external project imports are not."""
    package_root = pathlib.Path(__file__).parent.parent / "yasin_operations"
    forbidden_substrings = ("yasin_ai", "yasinai", "yasinpress", "yasinrelay")
    offending = []
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names = [node.module]
            else:
                continue
            for name in module_names:
                lowered = name.lower()
                if lowered.startswith("yasin_operations."):
                    continue
                if lowered == "hermes" or lowered.startswith("hermes."):
                    offending.append((str(path), name))
                elif any(term in lowered for term in forbidden_substrings):
                    offending.append((str(path), name))
    assert offending == [], f"Found forbidden external imports: {offending}"
