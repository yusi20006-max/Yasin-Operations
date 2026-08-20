# Executor Execution Semantics

## Authority order

1. `SafetyPolicy` decides whether execution is authorized.
2. `Executor` decides whether the request can safely proceed under resource, retry, cancellation, and execution-state rules.
3. `ToolCapability` declares whether retry is safe and, for mutations, whether the operation is idempotent.
4. The concrete Tool/backend owns cooperative execution and its own lower-level timeout mechanisms.

The Executor never grants authorization because a retry is requested.

## Retry contract

A retry is permitted only when all conditions hold:

- the policy allows more than one attempt;
- the Tool declares the operation `retryable`;
- the previous result is a retryable category (`timeout`, `unavailable_dependency`, or `execution_failure`);
- the outcome is not ambiguous;
- for mutating operations, the Tool declares the operation `idempotent`.

Validation failures, permission denials, cancellation, resource-limit failures, and ambiguous outcomes are never retried automatically.

Every attempt retains the same `operation_id` and `correlation_id`; the audit record identifies the attempt number and whether it was final.

## Timeout contract

The Executor cannot safely preempt arbitrary synchronous Python Tool code. It therefore enforces its budget at the execution boundary:

- before a retry, the remaining budget is checked;
- after a Tool returns, elapsed time is checked;
- a read-only operation that returns after the budget becomes `timeout`;
- a mutating operation that returns/raises after the budget becomes `ambiguous_outcome`, because the side effect may already have occurred.

Concrete backends should still enforce their own subprocess/network timeouts.

## Cancellation

`CancellationToken` provides cooperative cancellation. The Executor checks it before execution and between retries. Tools that cooperate may raise `OperationCancelledError` during their own work.

Cancellation is a terminal execution outcome and is audited. It is neither permission denial nor success.

## Ambiguous mutation rule

The system must fail closed when it cannot establish whether a mutation happened. Examples include:

- a mutating Tool raises `TimeoutError` after beginning work;
- a mutating Tool raises an unexpected exception after beginning work;
- a mutating Tool returns data that violates the result boundary after the action may already have happened;
- a mutating Tool exceeds the Executor budget.

Ambiguous mutations are never automatically retried.

## Resource boundaries

Executor-level limits protect the Core from pathological payloads and result objects:

- parameter byte size;
- parameter nesting depth;
- parameter item count;
- result byte size;
- JSON compatibility.

Gateway limits remain useful at the transport boundary. Executor limits remain necessary because other callers can bypass the gateway and invoke the Core directly.

## Audit invariants

Each execution attempt is attributable through:

- stable `operation_id`;
- stable `correlation_id`;
- actor/source identity;
- attempt number and maximum attempts;
- final/non-final marker;
- structured error category.

Audit is evidence only. An audit sink failure cannot grant permission, trigger a retry, or change the operation result.

## Production rule

When in doubt about whether a mutating action completed, report `ambiguous_outcome` and require an explicit reconciliation/read operation before another mutation. Never guess that the mutation did not happen.
