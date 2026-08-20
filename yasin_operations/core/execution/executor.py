"""Policy-enforced operation executor with deterministic failure semantics."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from yasin_operations.core.execution.cancellation import CancellationToken, OperationCancelledError
from yasin_operations.core.operations.models import Operation, OperationStatus
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.logging.audit import AuditRecord, AuditRecorder
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.contracts.tool import ToolCapability
from yasin_operations.tools.registry.registry import ToolRegistry


@dataclass(frozen=True)
class ExecutionLimits:
    max_parameter_bytes: int = 32 * 1024
    max_result_bytes: int = 64 * 1024
    max_parameter_depth: int = 8
    max_parameter_items: int = 256

    def __post_init__(self) -> None:
        if min(self.max_parameter_bytes, self.max_result_bytes, self.max_parameter_depth, self.max_parameter_items) <= 0:
            raise ValueError("execution resource limits must be positive")


class Executor:
    """Validate, authorize, execute, retry, cancel, bound, and audit tools."""

    _RETRYABLE_ERRORS = frozenset({ErrorCategory.TIMEOUT, ErrorCategory.UNAVAILABLE_DEPENDENCY, ErrorCategory.EXECUTION_FAILURE})

    def __init__(self, registry: ToolRegistry, *, policy: SafetyPolicy | None = None, audit_recorder: AuditRecorder | None = None, limits: ExecutionLimits | None = None) -> None:
        self.registry = registry
        self.policy = policy or SafetyPolicy()
        self.audit_recorder = audit_recorder
        self.limits = limits or ExecutionLimits()

    def execute(self, operation: Operation, *, actor: str = "system", source: str = "executor", confirmation: bool = False, dry_run: bool = False, correlation_id: str | None = None, cancellation_token: CancellationToken | None = None) -> OperationResult:
        self._validate_call_arguments(actor, source, confirmation, dry_run, correlation_id)
        correlation_id = correlation_id or str(uuid.uuid4())
        started = time.monotonic()
        token = cancellation_token or CancellationToken.create()
        parameter_error = self._validate_parameters(operation.parameters)
        if parameter_error is not None:
            result = OperationResult.fail(operation.id, parameter_error)
            self._audit(operation, OperationStatus.FAILED, result, actor=actor, source=source, correlation_id=correlation_id, started=started, metadata={"phase": "resource_validation"})
            return result

        matches = self.registry.find_for_operation(operation.name)
        if not matches:
            result = OperationResult.fail(operation.id, OperationError(ErrorCategory.UNSUPPORTED_OPERATION, f"No registered tool supports operation: {operation.name!r}"))
            self._audit(operation, OperationStatus.FAILED, result, actor=actor, source=source, correlation_id=correlation_id, started=started)
            return result
        tool = matches[0]
        capability = tool.descriptor.capability_for(operation.name)
        if capability is None or capability.safety_class != operation.safety_class:
            tool_class = capability.safety_class.value if capability is not None else "unknown"
            result = OperationResult.fail(operation.id, OperationError(ErrorCategory.VALIDATION_ERROR, "Operation safety_class does not match the tool's declared safety_class", {"operation": operation.safety_class.value, "tool": tool_class}))
            self._audit(operation, OperationStatus.FAILED, result, actor=actor, source=source, correlation_id=correlation_id, started=started)
            return result
        try:
            token.raise_if_cancelled()
        except OperationCancelledError as exc:
            result = OperationResult.fail(operation.id, OperationError(ErrorCategory.CANCELLED, str(exc), {"phase": "pre_execution"}))
            self._audit(operation, OperationStatus.CANCELLED, result, actor=actor, source=source, correlation_id=correlation_id, started=started, metadata={"phase": "pre_execution"})
            return result

        decision = self.policy.evaluate(operation, confirmation=confirmation, dry_run=dry_run)
        if dry_run:
            plan = dict(self.policy.plan(operation)); plan["tool_id"] = tool.descriptor.id
            result = OperationResult.ok(operation.id, plan)
            self._audit(operation, OperationStatus.SUCCEEDED, result, actor=actor, source=source, correlation_id=correlation_id, started=started, dry_run=True, metadata={"policy_reason": decision.reason, "tool_id": tool.descriptor.id})
            return result
        if decision.denied:
            result = OperationResult.fail(operation.id, OperationError(ErrorCategory.PERMISSION_DENIED, decision.reason, {"requires_confirmation": decision.requires_confirmation}))
            self._audit(operation, OperationStatus.DENIED, result, actor=actor, source=source, correlation_id=correlation_id, started=started, metadata={"policy_reason": decision.reason})
            return result

        attempts, retry_note = self._effective_attempts(decision.max_attempts, capability, operation.safety_class)
        last_result: OperationResult | None = None
        for attempt in range(1, attempts + 1):
            try:
                token.raise_if_cancelled()
            except OperationCancelledError as exc:
                last_result = OperationResult.fail(operation.id, OperationError(ErrorCategory.CANCELLED, str(exc), {"attempt": attempt}))
                self._audit_attempt(operation, last_result, actor, source, correlation_id, started, attempt, attempts, retry_note, final=True)
                return last_result
            if attempt > 1 and time.monotonic() - started >= self.policy.timeout_seconds:
                last_result = OperationResult.fail(operation.id, OperationError(ErrorCategory.TIMEOUT, "execution budget exhausted before retry", {"attempt": attempt, "max_attempts": attempts}))
                self._audit_attempt(operation, last_result, actor, source, correlation_id, started, attempt, attempts, retry_note, final=True)
                return last_result
            try:
                result = tool.execute(operation)
                elapsed = time.monotonic() - started
                if elapsed > self.policy.timeout_seconds:
                    category = ErrorCategory.AMBIGUOUS_OUTCOME if operation.safety_class is SafetyClass.MUTATING else ErrorCategory.TIMEOUT
                    last_result = OperationResult.fail(operation.id, OperationError(category, "tool execution exceeded the executor time budget", {"attempt": attempt, "elapsed_seconds": round(elapsed, 6)}))
                else:
                    last_result = self._bound_result(result, operation)
            except OperationCancelledError as exc:
                last_result = OperationResult.fail(operation.id, OperationError(ErrorCategory.CANCELLED, str(exc), {"attempt": attempt}))
            except TimeoutError as exc:
                category = ErrorCategory.AMBIGUOUS_OUTCOME if operation.safety_class is SafetyClass.MUTATING else ErrorCategory.TIMEOUT
                last_result = OperationResult.fail(operation.id, OperationError(category, str(exc) or "operation timed out", {"attempt": attempt}))
            except Exception as exc:  # noqa: BLE001
                category = ErrorCategory.AMBIGUOUS_OUTCOME if operation.safety_class is SafetyClass.MUTATING else ErrorCategory.INTERNAL_ERROR
                last_result = OperationResult.fail(operation.id, OperationError(category, f"Tool raised an unexpected exception: {exc}", {"tool_id": tool.descriptor.id, "attempt": attempt}))
            retry_allowed = self._can_retry(last_result, capability, operation.safety_class, attempt, attempts)
            final = last_result.success or not retry_allowed
            self._audit_attempt(operation, last_result, actor, source, correlation_id, started, attempt, attempts, retry_note, final=final)
            if final:
                return last_result
            try:
                token.raise_if_cancelled()
            except OperationCancelledError as exc:
                last_result = OperationResult.fail(operation.id, OperationError(ErrorCategory.CANCELLED, str(exc), {"attempt": attempt, "phase": "between_retries"}))
                self._audit_attempt(operation, last_result, actor, source, correlation_id, started, attempt, attempts, retry_note, final=True)
                return last_result
            time.sleep(min(0.01 * attempt, 0.1))
        raise AssertionError("executor reached an unreachable state")

    @staticmethod
    def _validate_call_arguments(actor: str, source: str, confirmation: bool, dry_run: bool, correlation_id: str | None) -> None:
        if not isinstance(actor, str) or not actor.strip(): raise ValueError("actor must be a non-empty string")
        if not isinstance(source, str) or not source.strip(): raise ValueError("source must be a non-empty string")
        if not isinstance(confirmation, bool): raise ValueError("confirmation must be a boolean")
        if not isinstance(dry_run, bool): raise ValueError("dry_run must be a boolean")
        if correlation_id is not None and (not isinstance(correlation_id, str) or not correlation_id.strip()): raise ValueError("correlation_id must be a non-empty string when provided")

    def _validate_parameters(self, parameters: Mapping[str, Any]) -> OperationError | None:
        try:
            self._walk(parameters, 0, [0])
            encoded = json.dumps(parameters, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, RecursionError) as exc:
            return OperationError(ErrorCategory.VALIDATION_ERROR, f"operation parameters are not JSON-compatible: {exc}")
        if len(encoded) > self.limits.max_parameter_bytes:
            return OperationError(ErrorCategory.RESOURCE_LIMIT, "operation parameters exceed the executor byte limit", {"limit": self.limits.max_parameter_bytes, "actual": len(encoded)})
        return None

    def _walk(self, value: Any, depth: int, count: list[int]) -> None:
        if depth > self.limits.max_parameter_depth: raise ValueError("parameter nesting exceeds executor depth limit")
        count[0] += 1
        if count[0] > self.limits.max_parameter_items: raise ValueError("parameter item count exceeds executor limit")
        if isinstance(value, Mapping):
            for key, item in value.items():
                if not isinstance(key, str): raise ValueError("parameter mapping keys must be strings")
                self._walk(item, depth + 1, count)
        elif isinstance(value, (list, tuple)):
            for item in value: self._walk(item, depth + 1, count)

    def _bound_result(self, result: OperationResult, operation: Operation) -> OperationResult:
        if not isinstance(result, OperationResult) or result.operation_id != operation.id:
            return OperationResult.fail(operation.id, OperationError(ErrorCategory.INTERNAL_ERROR, "tool returned an invalid OperationResult"))
        if result.data is None: return result
        try:
            encoded = json.dumps(result.data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, RecursionError) as exc:
            category = ErrorCategory.AMBIGUOUS_OUTCOME if operation.safety_class is SafetyClass.MUTATING else ErrorCategory.INTERNAL_ERROR
            return OperationResult.fail(operation.id, OperationError(category, f"tool result is not JSON-compatible: {exc}"))
        if len(encoded) > self.limits.max_result_bytes:
            category = ErrorCategory.AMBIGUOUS_OUTCOME if operation.safety_class is SafetyClass.MUTATING else ErrorCategory.RESOURCE_LIMIT
            return OperationResult.fail(operation.id, OperationError(category, "tool result exceeds the executor byte limit", {"limit": self.limits.max_result_bytes, "actual": len(encoded)}))
        return result

    @staticmethod
    def _effective_attempts(max_attempts: int, capability: ToolCapability, safety_class: SafetyClass) -> tuple[int, str | None]:
        if max_attempts <= 1: return 1, None
        if not capability.retryable: return 1, "retry_disabled_by_tool_capability"
        if safety_class is SafetyClass.MUTATING and not capability.idempotent: return 1, "mutation_not_declared_idempotent"
        return max_attempts, None

    def _can_retry(self, result: OperationResult, capability: ToolCapability, safety_class: SafetyClass, attempt: int, attempts: int) -> bool:
        if attempt >= attempts or not capability.retryable or result.success or result.error is None: return False
        if result.error.category not in self._RETRYABLE_ERRORS: return False
        return safety_class is SafetyClass.READ_ONLY or capability.idempotent

    def _audit_attempt(self, operation: Operation, result: OperationResult, actor: str, source: str, correlation_id: str, started: float, attempt: int, max_attempts: int, retry_note: str | None, *, final: bool) -> None:
        metadata: dict[str, object] = {"attempt": attempt, "max_attempts": max_attempts, "final": final}
        if retry_note: metadata["retry_note"] = retry_note
        self._audit(operation, OperationStatus.SUCCEEDED if result.success else OperationStatus.FAILED, result, actor=actor, source=source, correlation_id=correlation_id, started=started, metadata=metadata)

    def _audit(self, operation: Operation, status: OperationStatus, result: OperationResult, *, actor: str, source: str, correlation_id: str, started: float, dry_run: bool = False, metadata: dict[str, object] | None = None) -> None:
        if self.audit_recorder is None: return
        entry = AuditRecord(operation_id=operation.id, operation_name=operation.name, target=operation.target, status=status, error=result.error, metadata=metadata or {}, actor=actor, source=source, correlation_id=correlation_id, duration_ms=(time.monotonic() - started) * 1000, dry_run=dry_run)
        try: self.audit_recorder.record(entry)
        except Exception: return
