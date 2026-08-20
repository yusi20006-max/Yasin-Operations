# Runtime & Service Lifecycle Contract

## Purpose

`Yasin-Operations` reports **observed runtime state**. A lifecycle control command is not considered successful merely because its process returned exit code `0`.

The backend must observe the requested resulting state before returning success.

## State model

| State | Meaning |
| --- | --- |
| `unknown` | The backend cannot establish a trustworthy state. |
| `stopped` | The service is not observed running. |
| `starting` | Transitional state used by adapters when applicable. |
| `running` | The service is observed running. |
| `stopping` | Transitional state used by adapters when applicable. |
| `failed` | The backend observed a definite lifecycle/control failure. |
| `degraded` | The service is running/observable but does not match its desired state or health contract. |

## Mutation semantics

### Start

1. Validate the registered service definition.
2. Execute only the predefined backend action.
3. Poll status until `running` is observed.
4. If the process/service exits immediately, return a typed readiness failure.
5. If the lifecycle budget expires, return a typed timeout.

### Stop

1. Validate the registered service definition.
2. Execute the predefined stop action or configured signal.
3. Poll until `stopped` is observed.
4. A successful control command without an observed stop is not success.

### Restart

Restart is a lifecycle transaction at the backend boundary: the stop phase must complete before the start phase is accepted. A failed stop or start is surfaced as failure; the backend never claims success based only on the control command's exit code.

## Timeout semantics

The configured execution timeout bounds control commands and the lifecycle verification budget. Startup grace is additional settling time for slow runtimes. Timeout is represented by `ServiceTimeoutError`, which is also a `TimeoutError` so the Tool layer maps it to the canonical timeout result category.

## Unavailable backend

If the runit executable or service root is unavailable, mutating operations do **not** silently return the current unknown state as mutation success. They fail explicitly because the requested state cannot be established and no safe mutation can be claimed.

Read-only discovery may still return `unknown/unavailable` so diagnostics can explain the host condition.

## Failure isolation

`list_services()` must return an entry for every registered service even if one service has a missing directory, malformed state, or backend error. One broken service must not hide unrelated services from `status`, `health`, or `doctor`.

## Security boundary

Service names come from the registered configuration. Lifecycle commands use fixed argv arrays and never accept arbitrary shell strings. Lifecycle verification does not bypass `Executor` or `SafetyPolicy`; it only makes the backend's mutation result more trustworthy.

## Operational interpretation

- `running + health_state=ok`: desired runtime state is observed.
- `stopped` for a service whose desired state is `running`: degraded/unhealthy service state.
- `unknown/unavailable`: host/backend cannot establish state; treat as an operational fault, never as success.
- `failed`: lifecycle or control failure was observed.

This contract is intentionally backend-neutral. A future systemd or remote backend must preserve the same externally visible semantics.
