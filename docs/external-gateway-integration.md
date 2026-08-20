# External Gateway Integration and MCP Boundary

## Purpose

Yasin-Operations exposes a deliberately narrow local JSONL transport for external agent clients. The transport is a protocol boundary around the canonical Operations runtime; it is not itself an execution engine and it does not replace `Executor` or `SafetyPolicy`.

## Current transport

The supported gateway is the local JSONL gateway exposed by:

```text
python -m yasin_operations.gateway_cli
```

Each non-empty stdin line is one JSON request and each response is exactly one JSON line on stdout. Diagnostics and human-oriented output must not be written to stdout by the gateway process.

The gateway validates, before execution:

- schema version;
- envelope/request identity consistency;
- request identifiers and control characters;
- operation, target, actor, source and correlation identifiers;
- safety-class representation;
- parameter object shape and bounded serialized size;
- total request line size.

The adapter then delegates to the canonical `Executor`, which remains responsible for tool lookup, safety-policy evaluation, confirmation, dry-run behavior, execution and audit recording.

## Replay and request identity

Request IDs are tracked in a bounded in-memory ledger.

- A matching completed read-only request may return the exact cached response without executing again.
- A duplicate mutating request is rejected.
- Reusing a request ID for a different execution-relevant payload is rejected.
- Reusing an in-flight request ID is rejected.
- Old entries are evicted according to the configured bounded window.
- The ledger is intentionally process-local; persistence across process restarts is not claimed by this transport.

This mechanism is a transport-level replay/idempotency control. It is not a substitute for durable distributed idempotency when multiple gateway processes are used.

## Failure boundary

Malformed client input becomes a structured validation response. Unexpected internal exceptions are converted to stable generic internal-error responses so backend exception text is not disclosed through the external protocol.

Unavailable dependencies remain machine-readable through the response status and canonical error category.

## Process contract

The gateway process is safe to smoke-test without third-party credentials. The acceptance suite verifies:

- `--help` and `--version` remain machine-safe;
- stdin/stdout remains JSONL for request processing;
- stdout contains no banners or diagnostics;
- stderr is empty for normal smoke paths;
- EOF terminates cleanly;
- invalid input does not terminate the stream loop.

## MCP status

The JSONL gateway is **not MCP**.

No MCP initialize/discovery/tool-call protocol is claimed or implied by this gateway. Hermes may support MCP independently, but that external capability must not be conflated with the Yasin-Operations JSONL contract.

If Yasin-Operations later exposes an MCP server, it must be introduced as a separate explicit transport adapter with its own versioned contract and dedicated tests for at least:

1. initialization and protocol version negotiation;
2. capability discovery;
3. tool listing and schema exposure;
4. tool-call input validation;
5. safety-class and authorization propagation;
6. request identity/replay semantics;
7. structured error mapping;
8. disconnect/timeout behavior.

Existing JSONL tests must not be presented as MCP compliance tests.

## Security boundary

The gateway does not add arbitrary shell execution, network access, credential loading, privilege escalation, or policy bypass. External-agent access must continue to pass through the typed operation model, registered tool boundary, `SafetyPolicy`, and audit layer.

## Test matrix

| Area | Required coverage |
|---|---|
| Protocol | valid round trip, schema rejection, malformed JSON, non-object payload |
| Input hardening | identifier limits, control characters, parameter/line limits, strict booleans and enums |
| Replay | duplicate read-only, duplicate mutation, payload mismatch, eviction, in-flight reuse |
| Authorization | read-only, unconfirmed mutation, confirmed mutation, protected target |
| Execution semantics | dry-run, unavailable runtime, timeout/error mapping, identity propagation |
| Process | CLI help/version, JSONL stdout, clean stderr, EOF |
| MCP boundary | explicit non-MCP status and future implementation requirements |

The production acceptance gate should execute this matrix across every supported Python version before release.
