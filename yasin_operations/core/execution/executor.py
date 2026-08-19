"""Policy-enforced operation executor.

The executor remains platform-agnostic: concrete tools own execution,
while SafetyPolicy owns authorization and AuditRecorder owns the audit
sink.  No shell or arbitrary command execution is introduced here.
"""
from __future__ import annotations

import time
import uuid

from yasin_operations.core.operations.models import Operation, OperationStatus
from yasin_operations.core.results.models import (
    ErrorCategory,
    OperationError,
    OperationResult,
)
from yasin_operations.logging.audit import AuditRecord, AuditRecorder
from yasin_operations.safety.policy import SafetyPolicy
from yasin_operations.tools.registry.registry import ToolRegistry


class Executor:
    """Execute registered tools only after policy authorization."""

    def __init__(
        self,
        registry: ToolRegistry,
        *,
        policy: SafetyPolicy | None = None,
        audit_recorder: AuditRecorder | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or SafetyPolicy()
        self.audit_recorder = audit_recorder

    def execute(
        self,
        operation: Operation,
        *,
        actor: str = "system",
        source: str = "executor",
        confirmation: bool = False,
        dry_run: bool = False,
        correlation_id: str | None = None,
    ) -> OperationResult:
        if not actor.strip() or not source.strip():
            raise ValueError("actor and source must not be empty")
        correlation_id = correlation_id or str(uuid.uuid4())
        started = time.monotonic()

        decision = self.policy.evaluate(
            operation, confirmation=confirmation, dry_run=dry_run
        )
        if dry_run:
            result = OperationResult.ok(operation.id, self.policy.plan(operation))
            self._audit(
                operation,
                OperationStatus.SUCCEEDED,
                result,
                actor=actor,
                source=source,
                correlation_id=correlation_id,
                started=started,
                dry_run=True,
                metadata={"policy_reason": decision.reason},
            )
            return result

        if decision.denied:
            result = OperationResult.fail(
                operation.id,
                OperationError(
                    category=ErrorCategory.PERMISSION_DENIED,
                    message=decision.reason,
                    details={"requires_confirmation": decision.requires_confirmation},
                ),
            )
            self._audit(
                operation,
                OperationStatus.DENIED,
                result,
                actor=actor,
                source=source,
                correlation_id=correlation_id,
                started=started,
                metadata={"policy_reason": decision.reason},
            )
            return result

        matches = self.registry.find_for_operation(operation.name)
        if not matches:
            result = OperationResult.fail(
                operation.id,
                OperationError(
                    category=ErrorCategory.UNSUPPORTED_OPERATION,
                    message=f"No registered tool supports operation: {operation.name!r}",
                ),
            )
            self._audit(
                operation,
                OperationStatus.FAILED,
                result,
                actor=actor,
                source=source,
                correlation_id=correlation_id,
                started=started,
            )
            return result

        tool = matches[0]
        capability = tool.descriptor.capability_for(operation.name)
        if capability is not None and capability.safety_class != operation.safety_class:
            result = OperationResult.fail(
                operation.id,
                OperationError(
                    category=ErrorCategory.VALIDATION_ERROR,
                    message=(
                        "Operation safety_class does not match the tool's "
                        f"declared safety_class for {operation.name!r}: "
                        f"operation={operation.safety_class.value!r}, "
                        f"tool={capability.safety_class.value!r}"
                    ),
                ),
            )
            self._audit(
                operation,
                OperationStatus.FAILED,
                result,
                actor=actor,
                source=source,
                correlation_id=correlation_id,
                started=started,
            )
            return result

        attempts = decision.max_attempts
        last_result: OperationResult | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = tool.execute(operation)
                last_result = result
                if result.success or attempt == attempts:
                    self._audit(
                        operation,
                        OperationStatus.SUCCEEDED if result.success else OperationStatus.FAILED,
                        result,
                        actor=actor,
                        source=source,
                        correlation_id=correlation_id,
                        started=started,
                        metadata={"attempt": attempt, "max_attempts": attempts},
                    )
                    return result
            except TimeoutError as exc:
                last_result = OperationResult.fail(
                    operation.id,
                    OperationError(
                        category=ErrorCategory.TIMEOUT,
                        message=str(exc) or "operation timed out",
                        details={"attempt": attempt},
                    ),
                )
            except Exception as exc:  # noqa: BLE001 - convert tool failures to structured results
                last_result = OperationResult.fail(
                    operation.id,
                    OperationError(
                        category=ErrorCategory.INTERNAL_ERROR,
                        message=f"Tool raised an unexpected exception: {exc}",
                        details={"tool_id": tool.descriptor.id, "attempt": attempt},
                    ),
                )

            if attempt == attempts:
                self._audit(
                    operation,
                    OperationStatus.FAILED,
                    last_result,
                    actor=actor,
                    source=source,
                    correlation_id=correlation_id,
                    started=started,
                    metadata={"attempt": attempt, "max_attempts": attempts},
                )
                return last_result

        raise AssertionError("executor reached an unreachable state")

    def _audit(
        self,
        operation: Operation,
        status: OperationStatus,
        result: OperationResult,
        *,
        actor: str,
        source: str,
        correlation_id: str,
        started: float,
        dry_run: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if self.audit_recorder is None:
            return
        entry = AuditRecord(
            operation_id=operation.id,
            operation_name=operation.name,
            target=operation.target,
            status=status,
            error=result.error,
            metadata=metadata or {},
            actor=actor,
            source=source,
            correlation_id=correlation_id,
            duration_ms=(time.monotonic() - started) * 1000,
            dry_run=dry_run,
        )
        try:
            self.audit_recorder.record(entry)
        except Exception:
            # Audit sinks must not turn a completed operation into an
            # unstructured execution failure. Production sinks can
            # provide their own durable delivery guarantees.
            return
