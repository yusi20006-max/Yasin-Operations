"""Policy-enforced, deterministic operation executor."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Mapping

from yasin_operations.core.execution.cancellation import CancellationToken, OperationCancelled
from yasin_operations.core.operations.models import Operation, OperationStatus
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.logging.audit import AuditRecord, AuditRecorder
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.contracts.tool import ToolCapability
from yasin_operations.tools.registry.registry import ToolRegistry


class Executor:
    """Validate, authorize, execute, retry safely, and audit registered tools."""

    def __init__(self, registry: ToolRegistry, *, policy: SafetyPolicy | None = None,
                 audit_recorder: AuditRecorder | None = None,
                 max_parameter_bytes: int = 32 * 1024, max_parameter_items: int = 256,
                 max_parameter_depth: int = 8) -> None:
        if max_parameter_bytes < 256 or max_parameter_items < 1 or max_parameter_depth < 1:
            raise ValueError("invalid executor resource limits")
        self.registry = registry
        self.policy = policy or SafetyPolicy()
        self.audit_recorder = audit_recorder
        self.max_parameter_bytes = max_parameter_bytes
        self.max_parameter_items = max_parameter_items
        self.max_parameter_depth = max_parameter_depth

    def execute(self, operation: Operation, *, actor: str = "system", source: str = "executor",
                confirmation: bool = False, dry_run: bool = False,
                correlation_id: str | None = None,
                cancellation: CancellationToken | None = None) -> OperationResult:
        self._validate_inputs(actor, source, confirmation, dry_run, correlation_id)
        correlation_id = correlation_id or str(uuid.uuid4())
        started = time.monotonic()
        resource_error = self._validate_parameters(operation.parameters, operation.id)
        if resource_error:
            self._audit(operation, OperationStatus.FAILED, resource_error, actor, source, correlation_id, started)
            return resource_error

        matches = self.registry.find_for_operation(operation.name)
        if not matches:
            result = OperationResult.fail(operation.id, OperationError(
                ErrorCategory.UNSUPPORTED_OPERATION,
                f"No registered tool supports operation: {operation.name!r}"))
            self._audit(operation, OperationStatus.FAILED, result, actor, source, correlation_id, started)
            return result
        tool = matches[0]
        capability = tool.descriptor.capability_for(operation.name)
        if capability is None or capability.safety_class != operation.safety_class:
            tool_class = capability.safety_class.value if capability else "unknown"
            result = OperationResult.fail(operation.id, OperationError(
                ErrorCategory.VALIDATION_ERROR,
                "Operation safety_class does not match the tool's declared "
                f"safety_class for {operation.name!r}: operation={operation.safety_class.value!r}, tool={tool_class!r}"))
            self._audit(operation, OperationStatus.FAILED, result, actor, source, correlation_id, started)
            return result

        decision = self.policy.evaluate(operation, confirmation=confirmation, dry_run=dry_run)
        if dry_run:
            plan = dict(self.policy.plan(operation)); plan["tool_id"] = tool.descriptor.id
            result = OperationResult.ok(operation.id, plan)
            self._audit(operation, OperationStatus.SUCCEEDED, result, actor, source, correlation_id, started,
                        dry_run=True, metadata={"policy_reason": decision.reason, "tool_id": tool.descriptor.id})
            return result
        if decision.denied:
            result = OperationResult.fail(operation.id, OperationError(
                ErrorCategory.PERMISSION_DENIED, decision.reason,
                {"requires_confirmation": decision.requires_confirmation}))
            self._audit(operation, OperationStatus.DENIED, result, actor, source, correlation_id, started,
                        metadata={"policy_reason": decision.reason})
            return result

        token = cancellation or CancellationToken()
        attempts = self._attempt_budget(operation, capability, decision.max_attempts)
        for attempt in range(1, attempts + 1):
            try:
                token.raise_if_cancelled()
            except OperationCancelled as exc:
                result = OperationResult.fail(operation.id, OperationError(
                    ErrorCategory.CANCELLED, str(exc), {"attempt": attempt}))
                self._audit(operation, OperationStatus.CANCELLED, result, actor, source, correlation_id, started,
                            metadata={"attempt": attempt, "max_attempts": attempts})
                return result

            attempt_started = time.monotonic()
            try:
                result = tool.execute(operation)
                elapsed = time.monotonic() - attempt_started
                if elapsed > self.policy.timeout_seconds:
                    result = self._budget_result(operation, elapsed, attempt)
                elif token.cancelled and result.success:
                    result = self._post_cancel_result(operation, attempt)
            except TimeoutError as exc:
                result = self._timeout_result(operation, str(exc) or "operation timed out", attempt)
            except Exception as exc:  # noqa: BLE001
                result = OperationResult.fail(operation.id, OperationError(
                    ErrorCategory.INTERNAL_ERROR, f"Tool raised an unexpected exception: {exc}",
                    {"tool_id": tool.descriptor.id, "attempt": attempt}))

            self._audit(operation, OperationStatus.SUCCEEDED if result.success else OperationStatus.FAILED,
                        result, actor, source, correlation_id, started,
                        metadata={"attempt": attempt, "max_attempts": attempts, "tool_id": tool.descriptor.id})
            if result.success or attempt == attempts:
                return result
            if result.error and result.error.category in {
                ErrorCategory.AMBIGUOUS_OUTCOME, ErrorCategory.CANCELLED,
                ErrorCategory.PERMISSION_DENIED, ErrorCategory.VALIDATION_ERROR,
                ErrorCategory.RESOURCE_LIMIT,
            }:
                return result
            try:
                token.raise_if_cancelled()
            except OperationCancelled as exc:
                result = OperationResult.fail(operation.id, OperationError(
                    ErrorCategory.CANCELLED, str(exc), {"attempt": attempt}))
                self._audit(operation, OperationStatus.CANCELLED, result, actor, source, correlation_id, started,
                            metadata={"attempt": attempt, "max_attempts": attempts})
                return result
        raise AssertionError("executor reached an unreachable state")

    @staticmethod
    def _validate_inputs(actor: str, source: str, confirmation: bool, dry_run: bool,
                         correlation_id: str | None) -> None:
        if not isinstance(actor, str) or not actor.strip(): raise ValueError("actor must be a non-empty string")
        if not isinstance(source, str) or not source.strip(): raise ValueError("source must be a non-empty string")
        if not isinstance(confirmation, bool): raise ValueError("confirmation must be a boolean")
        if not isinstance(dry_run, bool): raise ValueError("dry_run must be a boolean")
        if correlation_id is not None and (not isinstance(correlation_id, str) or not correlation_id.strip()):
            raise ValueError("correlation_id must be a non-empty string when provided")

    def _validate_parameters(self, parameters: Mapping[str, Any], operation_id: str) -> OperationResult | None:
        try:
            encoded = json.dumps(parameters, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError, OverflowError) as exc:
            return OperationResult.fail(operation_id, OperationError(ErrorCategory.VALIDATION_ERROR,
                f"parameters are not JSON-serializable: {exc}"))
        if len(encoded.encode("utf-8")) > self.max_parameter_bytes:
            return OperationResult.fail(operation_id, OperationError(ErrorCategory.RESOURCE_LIMIT,
                "operation parameters exceed size limit", {"max_parameter_bytes": self.max_parameter_bytes}))
        count = 0
        def walk(value: Any, depth: int) -> bool:
            nonlocal count
            count += 1
            if count > self.max_parameter_items or depth > self.max_parameter_depth: return False
            if isinstance(value, Mapping): return all(walk(k, depth + 1) and walk(v, depth + 1) for k, v in value.items())
            if isinstance(value, (list, tuple)): return all(walk(v, depth + 1) for v in value)
            return True
        if not walk(parameters, 0):
            return OperationResult.fail(operation_id, OperationError(ErrorCategory.RESOURCE_LIMIT,
                "operation parameters exceed structural limits", {"max_parameter_items": self.max_parameter_items,
                "max_parameter_depth": self.max_parameter_depth}))
        return None

    @staticmethod
    def _attempt_budget(operation: Operation, capability: ToolCapability, requested: int) -> int:
        if requested <= 1 or not capability.retryable: return 1
        if operation.safety_class is SafetyClass.MUTATING and not capability.idempotent: return 1
        return requested

    def _timeout_result(self, operation: Operation, message: str, attempt: int) -> OperationResult:
        category = ErrorCategory.TIMEOUT if operation.safety_class is SafetyClass.READ_ONLY else ErrorCategory.AMBIGUOUS_OUTCOME
        return OperationResult.fail(operation.id, OperationError(category, message,
            {"attempt": attempt, "mutation_outcome": "unknown"}))

    def _budget_result(self, operation: Operation, elapsed: float, attempt: int) -> OperationResult:
        category = ErrorCategory.TIMEOUT if operation.safety_class is SafetyClass.READ_ONLY else ErrorCategory.AMBIGUOUS_OUTCOME
        return OperationResult.fail(operation.id, OperationError(category, "operation exceeded execution budget",
            {"attempt": attempt, "elapsed_seconds": elapsed, "timeout_seconds": self.policy.timeout_seconds}))

    @staticmethod
    def _post_cancel_result(operation: Operation, attempt: int) -> OperationResult:
        category = ErrorCategory.CANCELLED if operation.safety_class is SafetyClass.READ_ONLY else ErrorCategory.AMBIGUOUS_OUTCOME
        return OperationResult.fail(operation.id, OperationError(category,
            "cancellation raced with tool completion; mutating outcome is ambiguous" if category is ErrorCategory.AMBIGUOUS_OUTCOME
            else "operation was cancelled after tool execution completed", {"attempt": attempt}))

    def _audit(self, operation: Operation, status: OperationStatus, result: OperationResult,
               actor: str, source: str, correlation_id: str, started: float,
               *, dry_run: bool = False, metadata: dict[str, object] | None = None) -> None:
        if self.audit_recorder is None: return
        try:
            self.audit_recorder.record(AuditRecord(operation_id=operation.id, operation_name=operation.name,
                target=operation.target, status=status, error=result.error, metadata=metadata or {}, actor=actor,
                source=source, correlation_id=correlation_id, duration_ms=(time.monotonic() - started) * 1000,
                dry_run=dry_run))
        except Exception:
            return
