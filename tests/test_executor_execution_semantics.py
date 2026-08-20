"""Adversarial tests for retry, cancellation, ambiguity, and resource bounds."""
from __future__ import annotations

from yasin_operations.core.execution.cancellation import CancellationToken
from yasin_operations.core.execution.executor import ExecutionLimits, Executor
from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.logging.audit import InMemoryAuditRecorder
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class ScriptedTool:
    def __init__(self, safety: SafetyClass, outcomes, *, retryable=True, idempotent=False):
        self.outcomes = list(outcomes)
        self.calls = 0
        self._descriptor = ToolDescriptor(
            id="scripted",
            description="test tool",
            capabilities=(ToolCapability("run", safety, retryable=retryable, idempotent=idempotent),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation):
        self.calls += 1
        outcome = self.outcomes[min(self.calls - 1, len(self.outcomes) - 1)]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _operation(safety=SafetyClass.READ_ONLY, parameters=None):
    return Operation(
        name="run",
        target=OperationTarget(kind="test", identifier="one"),
        safety_class=safety,
        parameters=parameters or {},
    )


def _executor(tool, *, attempts=1, limits=None, audit=None):
    registry = ToolRegistry()
    registry.register(tool)
    policy = SafetyPolicy(max_read_only_attempts=attempts, max_mutating_attempts=attempts)
    return Executor(registry, policy=policy, audit_recorder=audit, limits=limits)


def _failure(category=ErrorCategory.EXECUTION_FAILURE):
    return OperationResult.fail("placeholder", OperationError(category, "temporary failure"))


def test_read_only_retry_reuses_operation_identity_and_audits_each_attempt():
    audit = InMemoryAuditRecorder()
    op = _operation()
    tool = ScriptedTool(SafetyClass.READ_ONLY, [OperationResult.fail(op.id, OperationError(ErrorCategory.EXECUTION_FAILURE, "retry")), OperationResult.ok(op.id, {"ok": True})])
    result = _executor(tool, attempts=2, audit=audit).execute(op, correlation_id="corr-1")

    assert result.success
    assert tool.calls == 2
    assert [entry.metadata["attempt"] for entry in audit.entries] == [1, 2]
    assert all(entry.correlation_id == "corr-1" for entry in audit.entries)


def test_mutation_retry_requires_idempotency_declaration():
    op = _operation(SafetyClass.MUTATING)
    tool = ScriptedTool(SafetyClass.MUTATING, [OperationResult.fail(op.id, OperationError(ErrorCategory.EXECUTION_FAILURE, "no retry")), OperationResult.ok(op.id)], retryable=True, idempotent=False)
    result = _executor(tool, attempts=3).execute(op, confirmation=True)

    assert not result.success
    assert result.error.category is ErrorCategory.EXECUTION_FAILURE
    assert tool.calls == 1


def test_idempotent_mutation_may_retry_retryable_failure():
    op = _operation(SafetyClass.MUTATING)
    tool = ScriptedTool(SafetyClass.MUTATING, [OperationResult.fail(op.id, OperationError(ErrorCategory.UNAVAILABLE_DEPENDENCY, "retry")), OperationResult.ok(op.id)], retryable=True, idempotent=True)
    result = _executor(tool, attempts=2).execute(op, confirmation=True)

    assert result.success
    assert tool.calls == 2


def test_mutating_timeout_exception_is_ambiguous_and_never_retried():
    op = _operation(SafetyClass.MUTATING)
    tool = ScriptedTool(SafetyClass.MUTATING, [TimeoutError("late timeout"), OperationResult.ok(op.id)], retryable=True, idempotent=True)
    result = _executor(tool, attempts=2).execute(op, confirmation=True)

    assert not result.success
    assert result.error.category is ErrorCategory.AMBIGUOUS_OUTCOME
    assert tool.calls == 1


def test_pre_execution_cancellation_is_structured():
    token = CancellationToken.create()
    token.cancel()
    op = _operation()
    tool = ScriptedTool(SafetyClass.READ_ONLY, [OperationResult.ok(op.id)])
    result = _executor(tool).execute(op, cancellation_token=token)

    assert not result.success
    assert result.error.category is ErrorCategory.CANCELLED
    assert tool.calls == 0


def test_cancellation_between_retries_is_structured():
    token = CancellationToken.create()
    op = _operation()

    class CancellingTool(ScriptedTool):
        def execute(self, operation):
            self.calls += 1
            token.cancel()
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.EXECUTION_FAILURE, "retry"))

    tool = CancellingTool(SafetyClass.READ_ONLY, [], retryable=True)
    result = _executor(tool, attempts=3).execute(op, cancellation_token=token)

    assert not result.success
    assert result.error.category is ErrorCategory.CANCELLED
    assert tool.calls == 1


def test_parameter_resource_limits_reject_before_tool_execution():
    op = _operation(parameters={"blob": "x" * 1000})
    tool = ScriptedTool(SafetyClass.READ_ONLY, [OperationResult.ok(op.id)])
    executor = _executor(tool, limits=ExecutionLimits(max_parameter_bytes=64, max_result_bytes=1024))
    result = executor.execute(op)

    assert not result.success
    assert result.error.category is ErrorCategory.RESOURCE_LIMIT
    assert tool.calls == 0


def test_parameter_depth_limit_rejects_pathological_payload():
    value = {}
    cursor = value
    for _ in range(10):
        cursor["nested"] = {}
        cursor = cursor["nested"]
    op = _operation(parameters=value)
    tool = ScriptedTool(SafetyClass.READ_ONLY, [OperationResult.ok(op.id)])
    result = _executor(tool, limits=ExecutionLimits(max_parameter_depth=3)).execute(op)

    assert not result.success
    assert result.error.category is ErrorCategory.VALIDATION_ERROR
    assert tool.calls == 0


def test_large_read_only_result_is_resource_limited():
    op = _operation()
    tool = ScriptedTool(SafetyClass.READ_ONLY, [OperationResult.ok(op.id, {"blob": "x" * 1000})])
    result = _executor(tool, limits=ExecutionLimits(max_result_bytes=64)).execute(op)

    assert not result.success
    assert result.error.category is ErrorCategory.RESOURCE_LIMIT


def test_large_mutating_result_is_ambiguous_not_success():
    op = _operation(SafetyClass.MUTATING)
    tool = ScriptedTool(SafetyClass.MUTATING, [OperationResult.ok(op.id, {"blob": "x" * 1000})], retryable=True, idempotent=True)
    result = _executor(tool, limits=ExecutionLimits(max_result_bytes=64)).execute(op, confirmation=True)

    assert not result.success
    assert result.error.category is ErrorCategory.AMBIGUOUS_OUTCOME
