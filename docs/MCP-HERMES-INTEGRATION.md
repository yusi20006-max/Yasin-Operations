# Hermes ↔ Yasin-Operations MCP Integration

This document defines the local integration boundary for Hermes clients that
need to inspect or operate Yasin-Operations.

## Architecture

- Hermes is the operator/client.
- `yasin_operations.mcp_server` is an optional MCP stdio adapter.
- Yasin-Operations Executor remains the authoritative execution path.
- `SafetyPolicy` remains authoritative for authorization and confirmation.
- JSONL remains the canonical component-scoped transport; MCP is an optional
  adapter and does not replace it.
- No network listener is required or enabled by this integration.

## Local server command

After installing the optional MCP extra, a host can launch:

```text
python -m yasin_operations.mcp_server
```

The server communicates exclusively over stdin/stdout using MCP stdio. Hosts
should launch it as a child process rather than treating the command as a
network service.

## Tool contract

The bridge exposes:

- `yasin_status` — read-only service state and aggregate summary.
- `yasin_health` — read-only runtime health, service state and resources.
- `yasin_doctor` — read-only Termux/runit diagnostics.
- `yasin_start` — mutating; explicit `confirmation=true` is required unless
  `dry_run=true`.
- `yasin_stop` — mutating; explicit `confirmation=true` is required unless
  `dry_run=true`.
- `yasin_restart` — mutating; explicit `confirmation=true` is required unless
  `dry_run=true`.

Mutation confirmation is enforced inside the bridge before the executor is
called, and confirmed mutations still pass through the central Executor and
SafetyPolicy.

## Verification

### Automated

`tests/test_mcp_integration.py` verifies both:

1. an in-process MCP client can discover and call the bridge; and
2. a real MCP stdio client can launch `python -m yasin_operations.mcp_server`,
   discover all expected tools, and verify that an unconfirmed mutation is
   denied.

These tests require the optional MCP dependency. When the extra is absent,
core tests remain independent of MCP.

### Manual Hermes smoke test

On the target Termux device, install MCP using one of the supported paths in
`docs/TERMUX-MCP-COMPATIBILITY.md`, then configure Hermes to launch the local
stdio command above. The smoke test is successful when Hermes can:

1. discover the six tools;
2. call `yasin_status`, `yasin_health` and `yasin_doctor` successfully;
3. receive a structured `permission_denied` result for an unconfirmed
   `yasin_restart`, `yasin_start` or `yasin_stop`; and
4. perform a confirmed mutation only when the normal Operations safety policy
   permits it.

A successful hosted CI run does not prove this target-device smoke test.
Likewise, a successful local JSONL gateway test does not prove MCP transport
connectivity.
