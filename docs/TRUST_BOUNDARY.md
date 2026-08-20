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

## Limits and replay behavior

The local JSONL gateway enforces bounded line and parameter sizes and maintains a bounded recent request-ID set. Duplicate behavior is deterministic within that configured window. This is a bounded duplicate guard, not a durable distributed idempotency store; process restart can reset the window.

## Non-goals

This document does not claim that the local JSONL gateway is an MCP server, nor does it claim authentication for the local transport. MCP and authenticated remote transports require separate explicit adapters and security contracts.
