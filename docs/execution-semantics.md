# Executor Execution Semantics

## Authority
`Executor` remains the execution boundary. `SafetyPolicy` authorizes an operation before any tool call, and tool descriptors declare whether an operation is retry-safe and idempotent.

## Retry
The policy supplies the maximum attempt budget. The Executor may use more than one attempt only when the tool capability explicitly declares `retryable=true`. Mutating operations additionally require `idempotent=true`. Validation, permission, cancellation, resource-limit, and ambiguous outcomes are never retried.

## Timeout
`SafetyPolicy.timeout_seconds` is an execution budget observed by the Executor. Python synchronous tool calls cannot be safely preempted by the Executor. Therefore an over-budget read-only operation becomes `timeout`; an over-budget or timeout mutating operation becomes `ambiguous_outcome` and is not automatically retried.

## Cancellation
`CancellationToken` is cooperative. The Executor checks it before an attempt and between attempts. If cancellation races with a completed read-only tool call, the result is `cancelled`. If it races with a mutating call, the outcome is `ambiguous_outcome` because the side effect cannot be safely inferred.

## Resource limits
The Executor validates JSON-serializable parameters before tool execution and enforces byte, item-count, and nesting-depth limits. Gateway limits remain a separate outer transport boundary.

## Audit
Attempts use the same operation and correlation identifiers. Retry decisions and terminal outcomes are auditable. Audit sink failures do not alter authorization or execution results.

## Safety invariant
An uncertain mutating operation fails closed. No retry, timeout handling, or cancellation path may weaken `SafetyPolicy` or introduce arbitrary shell/privileged execution.
