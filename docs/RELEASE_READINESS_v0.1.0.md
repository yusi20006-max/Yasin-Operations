# Yasin-Operations v0.1.0 — Release Readiness

## Purpose

This document records the repository-local release readiness statement for
Yasin-Operations `0.1.0` as a standalone Termux-first Operations component.

## Production capability summary

- Typed operations, Executor, SafetyPolicy, and structured results
- Optional Hermes adapter and local JSONL gateway
- Optional stdio MCP bridge (`yasin_operations.mcp_server`)
- Optional ecosystem adapters (Yasin-AI, YasinPress, YasinRelay)
- Unified audit and observability
- Retry, cancellation, idempotency, timeout and resource-limit controls
- Production CLI, configuration, packaging and optional local daemon/gateway
- Termux/runit integration with authoritative runtime-state normalization
- Canonical production acceptance harness
- External JSONL gateway with replay/abuse and authorization-boundary tests
- Release-readiness checks and CI acceptance gating
- Monitoring snapshot (`monitor` / `yasin_monitor`) and live acceptance classification

### Explicit MCP status

The local JSONL gateway remains the canonical component-scoped external-agent
interface. It is **not** itself an MCP server and does not open a network
listener.

An **optional** stdio MCP bridge is available via `yasin_operations.mcp_server`
when the `mcp` extra is installed (`pip install -e ".[mcp]"`). See
`docs/MCP-HERMES-INTEGRATION.md` and `docs/TERMUX-MCP-COMPATIBILITY.md`.

Hermes remains an optional client. Hermes CLI `mcp` commands on a host are not
evidence that the Yasin-Operations MCP bridge is configured or healthy.

## Package

- Version: `0.1.0`
- Supported Python: `>=3.11`
- CLI: `yasin-operations`
- Module entrypoint: `python -m yasin_operations`
- Runtime dependencies: none for the standalone Core

## Canonical verification

The canonical verification sequence is:

```text
python -m pytest -q
python scripts/production_acceptance.py --json
python scripts/release_readiness.py --json
python scripts/production_acceptance.py --live --json
```

The first three commands are repository/host verification surfaces. The
`--live` command is host-dependent and must only be reported when actually
executed against the target Termux/runit environment.

Hosted CI proves the configured repository test and acceptance matrix. It
does not prove the health of local services, credentials, network access,
or a particular Termux host.

## Evidence policy

Evidence is classified as:

- **Repository evidence:** source, tests, packaging metadata and checked-in
  documentation.
- **Hosted CI evidence:** GitHub Actions workflow results.
- **Live host evidence:** a time-bound operator run against the real
  Termux/runit environment.

No historical live result is treated as a current health claim. The earlier
14 PASS / 0 FAIL / 0 SKIP Termux verification remains historical evidence
only; it does not assert that those services are running now.

## Security boundary

- `SafetyClass.READ_ONLY` and `SafetyClass.MUTATING` remain explicit.
- Mutations require confirmation by default.
- Protected targets remain denied unless allowlisted.
- Dry-run never invokes the target tool.
- Diagnostics and audit records must not dump credentials or the environment.

## Monitoring Program closure

Independent production closure for the Monitoring Completion Program (P4)
is recorded in `docs/FINAL_PRODUCTION_CLOSURE_MONITORING_P4.md` (Issue #157).

## Scope boundary

The repository-local documentation and release-readiness record are
component-scoped. Cross-project architecture authority remains with
YASIN-DOCS where applicable.

This is a repository-local readiness statement, not an ecosystem-wide
architecture certification. Final production closure for the Monitoring
Completion Program is the independent audit in
`docs/FINAL_PRODUCTION_CLOSURE_MONITORING_P4.md`.
