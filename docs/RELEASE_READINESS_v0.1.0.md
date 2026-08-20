# Yasin-Operations v0.1.0 — Release Readiness

## Release scope

Yasin-Operations is an optional, standalone Operations Agent for the Yasin
ecosystem. Core operation does not require Hermes, Yasin-AI, YasinPress,
YasinRelay, another Yasin repository, or an external AI provider.

## Architecture status

The repository contains the following implemented and documented layers:

- Core operation contracts, lifecycle and execution foundation
- Runtime process/service/health/diagnostics layer
- Optional ecosystem adapters for Yasin-AI, YasinPress, YasinRelay and Hermes
- Centralized authorization and default-deny policy enforcement
- Unified audit and observability
- Retry, cancellation, idempotency, timeout and resource-limit controls
- Production CLI, configuration, packaging and optional local daemon/gateway
- Termux/runit integration with authoritative runtime-state normalization
- Canonical production acceptance harness
- External JSONL gateway with replay/abuse and authorization-boundary tests
- Release-readiness checks and CI acceptance gating

### Explicit MCP status

The local JSONL gateway is a transport-neutral external-agent interface.
It is **not** an MCP server. The repository currently contains no MCP SDK
implementation, MCP discovery surface, or MCP network listener.

Hermes remains an optional client/integration boundary. The fact that the
Hermes CLI exposes `mcp` commands does not constitute Yasin-Operations MCP
support. Any future MCP implementation must be a separate protocol adapter
with an explicit contract and dedicated initialization, discovery, tool-call,
security and failure-isolation tests.

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
- Authorization is enforced before tool execution.
- Mutating operations require explicit confirmation unless explicitly
  authorized by policy.
- Protected targets remain deny-by-default.
- Retry logic does not retry permission denial.
- Mutating retries require the declared idempotency contract.
- Cancellation, timeout and ambiguous-outcome paths fail closed where the
  external outcome cannot safely be established.
- Scheduler and adapters cannot bypass Executor/SafetyPolicy.
- No unrestricted shell execution or `shell=True` is introduced.
- No external Yasin package is a hard dependency.
- The standalone runtime does not require a network listener.
- Diagnostics and audit records must not dump credentials or the environment.

## Documentation reconciliation

The following documents are the authoritative repository-local operational
surfaces and are cross-referenced from the README:

- `docs/OPERATIONS-RUNBOOK.md`
- `docs/TRANSPORT-BOUNDARY.md`
- `docs/ARCHITECTURE-RECONCILIATION.md`
- `docs/AUTHORIZATION_MODEL.md`
- `docs/EXECUTION-SEMANTICS.md`
- `docs/GATEWAY-INTEGRATION-TEST-MATRIX.md`
- `docs/RELEASE_PROCESS.md`
- `docs/PRODUCTION-DOCUMENTATION-RECONCILIATION.md`

Claims are intentionally separated between implemented behavior, hosted-CI
evidence, and live-host evidence. Proposed ecosystem architecture is not
presented as implemented repository functionality.

## Release conclusion

The repository-local documentation and release-readiness record are
reconciled with the current implementation boundary. `Yasin-Operations`
remains a standalone `v0.1.0` Operations layer with an optional local JSONL
gateway and an explicitly unimplemented MCP protocol surface.

This is a repository-local readiness statement, not an ecosystem-wide
architecture certification. Final production closure still requires the
independent audit and release-closure phase defined by the production
completion program.
