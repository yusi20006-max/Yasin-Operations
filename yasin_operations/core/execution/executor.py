"""Operation execution abstraction.

The executor resolves an Operation to a registered Tool and invokes
it. It has no knowledge of shell commands, Termux, runit, Hermes, or
any specific execution technology -- those live behind adapters that
implement the Tool protocol in later issues.
"""

from __future__ import annotations

from yasin_operations.core.operations.models import Operation, OperationStatus
from yasin_operations.core.results.models import (
    ErrorCategory,
    OperationError,
    OperationResult,
)
from yasin_operations.tools.registry.registry import ToolRegistry


class Executor:
    """Executes operations by dispatching to a ToolRegistry.

    Deliberately does not implement retries, scheduling, or queuing
    -- that belongs to later issues (e.g. Issue #5's reliability
    work referenced for the wider Yasin ecosystem is explicitly out
    of this Issue's scope). This executor performs a single
    synchronous execution attempt per call.
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(self, operation: Operation) -> OperationResult:
        matches = self.registry.find_for_operation(operation.name)

        if not matches:
            return OperationResult.fail(
                operation.id,
                OperationError(
                    category=ErrorCategory.UNSUPPORTED_OPERATION,
                    message=f"No registered tool supports operation: {operation.name!r}",
                ),
            )

        tool = matches[0]
        capability = tool.descriptor.capability_for(operation.name)

        if capability is not None and capability.safety_class != operation.safety_class:
            return OperationResult.fail(
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

        try:
            return tool.execute(operation)
        except Exception as exc:  # noqa: BLE001 - convert any tool exception to a structured result
            return OperationResult.fail(
                operation.id,
                OperationError(
                    category=ErrorCategory.INTERNAL_ERROR,
                    message=f"Tool raised an unexpected exception: {exc}",
                    details={"tool_id": tool.descriptor.id},
                ),
            )
