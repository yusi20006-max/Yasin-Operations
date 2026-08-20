# External Gateway Integration Test Matrix

## Current boundary

The canonical Yasin-Operations external component transport is JSONL over stdin/stdout. The repository is **not an MCP server**. The existing transport decision is documented in `docs/TRANSPORT-BOUNDARY.md`.

## Matrix

| Area | Required verification |
| --- | --- |
| Envelope | valid JSON object, schema version, required fields |
| Parsing | malformed JSON, arrays, null, scalar payloads |
| Identity | request ID, actor/source, target, correlation ID validation |
| Limits | line bytes, parameter bytes, identifier length |
| Replay | duplicate rejection, bounded replay window, eviction |
| Authorization | read-only, unconfirmed mutation, confirmed mutation, protected targets |
| Dry-run | policy plan returned, tool not executed |
| Runtime failure | unavailable dependency, timeout, structured failure |
| Stream behavior | multiple lines, bad line followed by good line, EOF, stop |
| Process smoke | gateway module help/CLI contract, stdout/stderr separation |
| Errors | canonical category/status mapping and stable machine-readable envelope |
| MCP | explicit non-implementation; no accidental MCP dependency or claim |

## Credential policy

The suite is offline and credential-free. It must not require Telegram, Hermes, Yasin-AI, YasinPress, YasinRelay, network access, or a live service host.

## Mutation safety

Integration tests may submit a mutating request to the typed fake Executor boundary to prove authorization propagation, but they must not perform a real mutation. Duplicate mutation requests must prove that transport replay protection prevents a second Executor invocation.

## MCP rule

Do not test JSONL as if it were MCP. If MCP is introduced later, create a separate issue and adapter contract with MCP initialize, discovery, tool-call, error, cancellation, and authorization tests. The current acceptance condition is that the repository makes no false MCP claim.
