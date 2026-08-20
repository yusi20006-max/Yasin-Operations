"""Adversarial execution semantics tests for Issue #127."""
from __future__ import annotations

import time

from yasin_operations.core.execution.cancellation import CancellationToken
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class CountingTool:
    def __init__(self, *, safety=SafetyClass.READ_ONLY, retryable=False, idempotent=False,
                 failures=0, delay=0.0):
        self.calls = 0
        self.failures = failures
        self.delay = delay
        self._descriptor = ToolDescriptor(
            id="counting", description="deterministic test tool",
            capabilities=(ToolCapability("run", safety, retryable, idempotent),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.calls <= self.failures:
            return OperationResult.fail(operation.id, OperationError(
                ErrorCategory.EXECUTION_FAILURE, "planned failure"))
        return OperationResult.ok(operation.id, {"calls": self.calls})


def _operation(safety=SafetyClass.READ_ONLY, parameters=None):
    return Operation(name="run", target=OperationTarget("service", "x"),
                     safety_class=safety, parameters=parameters or {})


def _executor(tool, policy=None, **kwargs):
    registry = ToolRegistry()
    registry.register(tool)
    return Executor(registry, policy=policy, **kwargs)


def test_read_only_retry_requires_explicit_retryable_capability():
    tool = CountingTool(failures=1, retryable=False)
    executor = _executor(tool, SafetyPolicy(max_read_only_attempts=3))
    result = executor.execute(_operation())
    assert not result.success
    assert tool.calls == 1


def test_read_only_retry_retries_only_retryable_tool():
    tool = CountingTool(failures=1, retryable=True)
    executor = _executor(tool, SafetyPolicy(max_read_only_attempts=3))
    result = executor.execute(_operation())
    assert result.success
    assert tool.calls == 2


def test_mutating_retry_requires_idempotency():
    tool = CountingTool(safety=SafetyClass.MUTATING, retryable=True, idempotent=False, failures=1)
    policy = SafetyPolicy(max_mutating_attempts=3)
    executor = _executor(tool, policy)
    result = executor.execute(_operation(SafetyClass.MUTATING), confirmation=True)
    assert not result.success
    assert tool.calls == 1


def test_idempotent_mutation_can_retry_after_structured_failure():
    tool = CountingTool(safety=SafetyClass.MUTATING, retryable=True, idempotent=True, failures=1)
    executor = _executor(tool, SafetyPolicy(max_mutating_attempts=3))
    result = executor.execute(_operation(SafetyClass.MUTATING), confirmation=True)
    assert result.success
    assert tool.calls == 2


def test_mutating_timeout_fails_closed_as_ambiguous():
    tool = CountingTool(safety=SafetyClass.MUTATING, delay=0.01)
    policy = SafetyPolicy(timeout_seconds=0.001)
    result = _executor(tool, policy).execute(_operation(SafetyClass.MUTATING), confirmation=True)
    assert not result.success
    assert result.error.category == ErrorCategory.AMBIGUOUS_OUTCOME
    assert tool.calls == 1


def test_cancellation_before_execution_is_typed_and_no_tool_call_occurs():
    tool = CountingTool()
    token = CancellationToken()
    token.cancel()
    result = _executor(tool).execute(_operation(), cancellation=token)
    assert not result.success
    assert result.error.category == ErrorCategory.CANCELLED
    assert tool.calls == 0


def test_cancellation_between_retries_stops_before_next_attempt():
    class CancelAfterFirst(CountingTool):
        def execute(self, operation):
            result = super().execute(operation)
            token.cancel()
            return result

    token = CancellationToken()
    tool = CancelAfterFirst(failures=1, retryable=True)
    executor = _executor(tool, SafetyPolicy(max_read_only_attempts=3))
    result = executor.execute(_operation(), cancellation=token)
    assert not result.success
    assert result.error.category == ErrorCategory.CANCELLED
    assert tool.calls == 1


def test_parameter_size_is_rejected_before_tool_execution():
    tool = CountingTool()
    executor = _executor(tool, max_parameter_bytes=256)
    result = executor.execute(_operation(parameters={"payload": "x" * 1000}))
    assert not result.success
    assert result.error.category == ErrorCategory.RESOURCE_LIMIT
    assert tool.calls == 0


def test_parameter_depth_is_rejected_before_tool_execution():
    value = {}
    for _ in range(12):
        value = {"nested": value}
    tool = CountingTool()
    executor = _executor(tool, max_parameter_depth=4)
    result = executor.execute(_operation(parameters=value))
    assert not result.success
    assert result.error.category == ErrorCategory.RESOURCE_LIMIT
    assert tool.calls == 0
