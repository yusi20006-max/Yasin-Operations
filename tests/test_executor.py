import pytest

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.logging.audit import InMemoryAuditRecorder
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


def _target():
    return OperationTarget(kind="service", identifier="x")


class SucceedingTool:
    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="succeeding-tool",
            description="always succeeds",
            capabilities=(ToolCapability("do_thing", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        return OperationResult.ok(operation.id, data={"ok": True})


class FailingTool:
    """A tool that returns a structured failure (not an exception)."""

    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="failing-tool",
            description="always fails cleanly",
            capabilities=(ToolCapability("do_thing", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        return OperationResult.fail(
            operation.id,
            OperationError(category=ErrorCategory.EXECUTION_FAILURE, message="failed on purpose"),
        )


class RaisingTool:
    """A tool that raises instead of returning a structured result."""

    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="raising-tool",
            description="raises unexpectedly",
            capabilities=(ToolCapability("do_thing", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        raise RuntimeError("unexpected failure")


class MutatingCapabilityTool:
    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="mutating-tool",
            description="declares mutating",
            capabilities=(ToolCapability("do_thing", SafetyClass.MUTATING),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        return OperationResult.ok(operation.id)


def test_execute_successful_operation():
    registry = ToolRegistry()
    registry.register(SucceedingTool())
    executor = Executor(registry)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)
    result = executor.execute(op)

    assert result.success is True
    assert result.data == {"ok": True}


def test_execute_failing_operation_returns_structured_error():
    registry = ToolRegistry()
    registry.register(FailingTool())
    executor = Executor(registry)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)
    result = executor.execute(op)

    assert result.success is False
    assert result.error.category == ErrorCategory.EXECUTION_FAILURE


def test_execute_unsupported_operation():
    registry = ToolRegistry()
    executor = Executor(registry)

    op = Operation(name="nonexistent_op", target=_target(), safety_class=SafetyClass.READ_ONLY)
    result = executor.execute(op)

    assert result.success is False
    assert result.error.category == ErrorCategory.UNSUPPORTED_OPERATION


def test_execute_tool_that_raises_is_converted_to_internal_error():
    registry = ToolRegistry()
    registry.register(RaisingTool())
    executor = Executor(registry)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)
    result = executor.execute(op)

    assert result.success is False
    assert result.error.category == ErrorCategory.INTERNAL_ERROR
    assert "unexpected failure" in result.error.message


def test_execute_rejects_safety_class_mismatch():
    registry = ToolRegistry()
    registry.register(MutatingCapabilityTool())
    executor = Executor(registry)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)
    result = executor.execute(op)

    assert result.success is False
    assert result.error.category == ErrorCategory.VALIDATION_ERROR


def test_execute_matching_mutation_requires_confirmation():
    registry = ToolRegistry()
    registry.register(MutatingCapabilityTool())
    audit = InMemoryAuditRecorder()
    executor = Executor(registry, audit_recorder=audit)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.MUTATING)
    denied = executor.execute(op)
    assert denied.success is False
    assert denied.error.category == ErrorCategory.PERMISSION_DENIED

    allowed = executor.execute(op, actor="operator", source="test", confirmation=True)
    assert allowed.success is True
    assert audit.entries[-1].actor == "operator"
    assert audit.entries[-1].source == "test"


def test_execute_dry_run_never_reaches_tool():
    class ExplodingTool(SucceedingTool):
        def execute(self, operation: Operation) -> OperationResult:
            raise AssertionError("dry-run executed the tool")

    registry = ToolRegistry()
    registry.register(ExplodingTool())
    executor = Executor(registry)
    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)

    result = executor.execute(op, dry_run=True)
    assert result.success is True
    assert result.data["dry_run"] is True


def test_protected_target_is_denied_even_with_confirmation():
    registry = ToolRegistry()
    registry.register(MutatingCapabilityTool())
    policy = SafetyPolicy.with_protected_targets(
        {("service", "x")}, protected_mutation_allowlist=set()
    )
    executor = Executor(registry, policy=policy)
    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.MUTATING)

    result = executor.execute(op, confirmation=True)
    assert result.success is False
    assert result.error.category == ErrorCategory.PERMISSION_DENIED


def test_executor_rejects_truthy_string_confirmation():
    registry = ToolRegistry()
    registry.register(MutatingCapabilityTool())
    executor = Executor(registry)
    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.MUTATING)

    with pytest.raises(ValueError, match="confirmation must be a boolean"):
        executor.execute(op, confirmation="true")


def test_executor_rejects_truthy_string_dry_run():
    registry = ToolRegistry()
    registry.register(SucceedingTool())
    executor = Executor(registry)
    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)

    with pytest.raises(ValueError, match="dry_run must be a boolean"):
        executor.execute(op, dry_run="true")


def test_executor_rejects_non_string_identity_fields():
    registry = ToolRegistry()
    registry.register(SucceedingTool())
    executor = Executor(registry)
    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)

    with pytest.raises(ValueError, match="actor must be a non-empty string"):
        executor.execute(op, actor=123)
    with pytest.raises(ValueError, match="source must be a non-empty string"):
        executor.execute(op, source=123)
    with pytest.raises(ValueError, match="correlation_id must be a non-empty string"):
        executor.execute(op, correlation_id=123)
