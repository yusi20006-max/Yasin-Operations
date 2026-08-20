# External Request Trust Boundary

## Scope

`Yasin-Operations` treats JSONL gateway and Hermes adapter input as untrusted external data. External requests must become typed Core operations only after validation.

## Validation boundary

The gateway validates, before calling the adapter:

- JSON envelope shape and schema version.
- Request object shape and unknown-field rejection.
- Exact string types for operation, target, actor, source, request IDs, and correlation IDs.
- Exact boolean types for `confirmation` and `dry_run`.
- `SafetyClass` values.
- Parameter object shape and serialized size.
- Identifier length and control-character restrictions.
- Envelope/request `request_id` consistency.
- Bounded duplicate request-ID tracking.

The Hermes contract repeats the type and shape validation so callers that use the adapter directly cannot rely on gateway-only coercion behavior.

## Identity semantics

`actor` and `source` are metadata supplied to the Executor and audit layer. They are not authentication credentials. A transport that cannot establish caller identity must not represent a caller as trusted merely by accepting arbitrary identity strings.

Future authenticated transports should establish identity at the transport boundary and inject the verified identity rather than trusting client-provided identity claims.

## Authorization boundary

Validation does not authorize operations. After validation, every operation continues through the existing `Executor` and `SafetyPolicy`. Mutating operations therefore remain subject to confirmation and protected-target policy.

`dry_run` is a planning mode and must never be used as an authorization bypass.

## Error disclosure

External boundaries return stable categories and generic messages for unexpected internal failures. Validation errors may identify the invalid public field, but internal exception text, filesystem paths, credentials, stack traces, and dependency details must not be exposed to untrusted clients.

## Idempotency, replay, and request lifecycle

The local JSONL gateway uses a bounded in-memory request ledger keyed by `request_id` and a SHA-256 fingerprint of execution-relevant fields.

- **Read-only request:** a repeated request with the same ID and identical fingerprint replays the cached response without invoking the tool again.
- **Mutating request:** a repeated request ID is rejected, even when the fingerprint is identical. This gives at-most-once behavior within the active ledger window rather than risking a second mutation.
- **Conflicting reuse:** reusing an ID for a different request is rejected.
- **Concurrent reuse:** an ID already executing is rejected until the first request completes.
- **Eviction:** the ledger is bounded. Once an ID leaves the configured window, the gateway no longer has local evidence that it was previously executed.
- **Restart:** the ledger is process-local and is lost on restart. It is not a durable distributed idempotency store.

Callers requiring durable exactly-once or cross-process deduplication must use a persistent idempotency mechanism outside this local gateway contract.

`correlation_id` is a tracing/audit correlation value; it is not itself an idempotency key and does not authorize execution.

## Non-goals

This document does not claim that the local JSONL gateway is an MCP server, nor does it claim authentication for the local transport. MCP and authenticated remote transports require separate explicit adapters and security contracts.
