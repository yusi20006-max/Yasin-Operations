# Production Documentation Reconciliation

## Purpose

This document records the repository-local documentation reconciliation for
P2.3. It is intentionally evidence-oriented: implemented behavior, hosted
CI evidence and live-host evidence are separate categories.

## Current architecture boundary

| Surface | Current status | Evidence boundary |
|---|---|---|
| Core operations | Implemented | Source + unit/integration tests |
| Executor / SafetyPolicy | Implemented | Source + safety/executor tests |
| Runtime health/diagnostics | Implemented | Runtime tests + acceptance harness |
| Termux/runit adapter | Implemented | Source + host-dependent live checks |
| Ecosystem adapters | Optional and contract-bounded | Adapter contract + failure-isolation tests |
| Hermes adapter | Optional interface boundary | Adapter tests; Hermes itself is external |
| Local JSONL gateway | Implemented | Gateway contract + adversarial integration tests |
| MCP server | **Not implemented** | No MCP SDK/server/discovery surface in repository |
| Network gateway | Not implemented by default | JSONL gateway is local stdin/stdout only |
| Standalone Core dependency on Yasin services | None | Packaging/import independence tests |

## JSONL vs MCP

The repository deliberately distinguishes the local JSONL gateway from MCP.
JSONL is a bounded, local, transport-neutral protocol around the typed
Operations contract. It does not expose MCP initialization, capability
discovery, tool schemas or MCP tool calls.

The existence of `hermes mcp` commands on an installed Hermes client is not
evidence that this repository implements MCP. Hermes is an optional external
client boundary.

If MCP becomes an architectural requirement, it must be implemented as a
separate adapter with:

1. explicit MCP SDK/dependency policy;
2. initialize and capability-negotiation tests;
3. tool discovery and schema tests;
4. tool-call to typed Operation translation tests;
5. authorization and confirmation propagation tests;
6. replay, malformed-input and failure-isolation tests;
7. explicit local/network exposure policy.

Existing JSONL tests must not be reused as a substitute for those MCP tests.

## Operational runbook boundary

Operators should use the following commands for repository-local state:

```sh
python -m yasin_operations status
python -m yasin_operations health
python -m yasin_operations doctor
python -m yasin_operations start <service>
python -m yasin_operations stop <service>
python -m yasin_operations restart <service> --dry-run
python -m yasin_operations restart <service> --confirm
```

Machine-readable consumers should use `--json` where supported.

The local gateway is started with:

```sh
yasin-operations gateway
```

It communicates through newline-delimited JSON on stdin/stdout and does not
open a network listener.

## Security and trust boundary

All external operation requests must become typed `Operation` objects and
pass through the canonical `Executor` and `SafetyPolicy` before a registered
tool executes.

The documentation therefore does not describe adapters as authorization
layers. Adapters translate and validate at the boundary; Core remains the
execution authority.

Mutation confirmation, protected-target policy, idempotency requirements,
resource limits, cancellation, timeout handling and audit behavior remain
Core concerns.

## Evidence model

### Repository evidence

Includes source code, tests, packaging metadata and checked-in acceptance
scripts. This is the authoritative evidence for what the repository contains.

### Hosted CI evidence

GitHub Actions can verify the configured Python/test/packaging matrix. Hosted
CI does not prove the health of a particular user's Termux services or local
credentials.

### Live host evidence

`production_acceptance.py --live --json` is an operator/host verification
surface. Its result is time-bound. Historical live results must not be
presented as current service health.

## Release-readiness reconciliation

The v0.1.0 release-readiness document now records the current protocol and
evidence boundaries. In particular, the previous historical live result is
retained only as historical evidence and is no longer phrased as a current
health assertion.

## Source-of-truth rule

YASIN-DOCS remains the cross-project architectural source of truth. This
repository's documentation is authoritative for repository-local behavior,
but it must not promote proposed ecosystem architecture into an implemented
claim without corresponding code and verification evidence.

## P2.3 completion criteria

- [x] README reconciled with current implementation boundaries.
- [x] JSONL gateway documented separately from MCP.
- [x] Hermes integration documented as optional external boundary.
- [x] Operational command/runbook surface identified.
- [x] Security/trust boundary documented.
- [x] Hosted CI and live-host evidence explicitly separated.
- [x] Release-readiness record reconciled.
- [x] Historical live evidence no longer represented as current health.
- [x] Cross-project architecture claims explicitly delegated to YASIN-DOCS.
