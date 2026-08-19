import pytest

from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.safety.classification import SafetyClass
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
    registry = ToolRegistry()  # no tools registered
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
    """An operation claiming READ_ONLY against a tool that declares
    MUTATING for the same operation name must be rejected rather than
    silently executed -- this is the executor's defense against a
    caller misrepresenting an operation's safety class."""
    registry = ToolRegistry()
    registry.register(MutatingCapabilityTool())
    executor = Executor(registry)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.READ_ONLY)
    result = executor.execute(op)

    assert result.success is False
    assert result.error.category == ErrorCategory.VALIDATION_ERROR


def test_execute_matching_safety_class_succeeds():
    registry = ToolRegistry()
    registry.register(MutatingCapabilityTool())
    executor = Executor(registry)

    op = Operation(name="do_thing", target=_target(), safety_class=SafetyClass.MUTATING)
    result = executor.execute(op)

    assert result.success is True


def test_execute_denied_operation_never_reaches_tool():
    """Simulates a 'denied' path: caller does not even attempt
    execution when authorization has already denied the operation.
    The executor itself has no authorization concept (that is a
    future layer) -- this test documents that denial is expected to
    happen before Executor.execute() is called at all."""
    registry = ToolRegistry()
    registry.register(SucceedingTool())
    executor = Executor(registry)

    # No tool call happens; a denial decision made upstream simply
    # never calls executor.execute(). This is a structural test
    # confirming Executor has no override/bypass for such a decision.
    assert not hasattr(executor, "force_execute")
