# Yasin-Operations

Modular Operations Agent for the Yasin ecosystem.

## Independence

This repository is standalone. It does not require Hermes, Yasin-AI,
YasinPress, YasinRelay, another Yasin repository, an external AI
provider, or a running external service to import and operate its Core.
All integrations are optional adapters around Core contracts.

## Package

Current release: `0.1.0`.

Supported Python: `>=3.11`. Hosted CI is intended to verify Python 3.11,
3.12, 3.13, and 3.14.

## Package layout

```text
yasin_operations/
    core/                 Operations, execution, results
    runtime/              Process/service/health/diagnostics runtime layer
    runtime/termux/       Optional Termux/runit adapter and configuration
    adapters/hermes/      Optional Hermes-facing interface boundary
    adapters/ecosystem/   Optional Yasin service adapters
    safety/               SafetyClass + deny-by-default SafetyPolicy
    logging/              Structured audit trail
    gateway.py            Optional local JSONL Operations Gateway
    gateway_cli.py        Gateway command implementation
    entrypoint.py         Installed CLI router
    version.py            Authoritative package version
    cli.py                 Standalone operations CLI
    daemon.py             Optional supervised always-on daemon
```

## Safety boundary

Every operation has an explicit `SafetyClass`. Mutations are denied
without explicit confirmation by default. Protected targets, dry-run,
retry limits, timeouts, actor/source attribution, correlation IDs, and
audit records are handled by the Core Executor and SafetyPolicy.
Adapters cannot bypass that boundary.

## CLI

```sh
python -m yasin_operations doctor
python -m yasin_operations status
python -m yasin_operations health
python -m yasin_operations restart <service> --dry-run
python -m yasin_operations restart <service> --confirm
yasin-operations --version
```

Use `--json` for machine-readable output. The installed console entrypoint
and `python -m yasin_operations` share the same authoritative package
version.

### Local Operations Gateway

The optional gateway provides a transport-neutral JSONL interface for
external agents such as Hermes. It uses the existing typed operation
contracts and Executor policy boundary; it does not import or control
Hermes itself and does not open a network listener.

```sh
yasin-operations gateway
```

Requests are newline-delimited JSON. The gateway validates the envelope,
converts it to a typed operation request, and emits one machine-readable
response per request. Malformed requests are isolated to their own
response and do not terminate the gateway loop.

The gateway is intentionally local and optional. Existing CLI commands,
runtime services, and standalone operation remain unchanged when it is
not used.

**Transport boundary:** the JSONL gateway is **not an MCP server**. There
is currently no MCP implementation in Yasin-Operations and Hermes MCP
configuration is an external client concern. A future MCP integration,
if required by the ecosystem architecture, must be introduced as a
separate protocol adapter with its own contract, discovery, tool-call,
and security tests. JSONL verification must not be represented as MCP
verification.

## Termux / runit

The optional always-on service definition is under
`deploy/termux/runit/yasin-operations/`. It runs the standalone daemon
under `runit`; it does not modify existing Hermes, Yasin-AI, YasinPress,
or YasinRelay service definitions.

Runtime configuration is environment-backed, including the runit
service root, `sv` path, registered service names, execution timeout,
and health interval.

Runit status is interpreted from its authoritative status prefix rather
than its process-independent exit code:

- `run:` -> actual `running` / healthy
- `down:` -> actual `stopped`
- `fail:` or `timeout:` -> actual `failed`
- unknown status text -> actual `unknown`

`desired_state` is separate from actual runtime state. In particular,
`down: ... normally up` means the service is currently stopped even if
runit is configured to keep it supervised.

## Production acceptance and release readiness

The canonical read-only acceptance harness is:

```sh
python scripts/production_acceptance.py
python scripts/production_acceptance.py --json
python scripts/production_acceptance.py --live --json
```

The normal CI workflow covers the non-live acceptance surface. Live
service health is an operator/host verification step and must never be
inferred from hosted CI results.

Release-readiness checks are available with:

```sh
python scripts/release_readiness.py --json
```

The canonical release procedure and the distinction between hosted CI
and live host verification are defined in `docs/RELEASE_PROCESS.md`.

## Verification evidence policy

Documentation deliberately distinguishes three evidence classes:

1. **Repository evidence** — source code, tests, packaging metadata, and
   checked-in acceptance/release artifacts.
2. **Hosted CI evidence** — workflow results produced by GitHub Actions;
   these do not prove the health of a user's local services.
3. **Live host evidence** — operator-run Termux/runit verification; this
   is time-bound and must not be presented as a current health claim
   unless a fresh live run is available.

The repository does not treat the presence of a Hermes CLI or Hermes MCP
command as evidence that Yasin-Operations implements MCP connectivity.

## Documentation map

- `docs/OPERATIONS-RUNBOOK.md` — operator workflows for status, health,
  diagnostics and lifecycle actions.
- `docs/TRANSPORT-BOUNDARY.md` — external transport and trust boundary,
  including the explicit JSONL-vs-MCP distinction.
- `docs/ARCHITECTURE-RECONCILIATION.md` — architecture/source-of-truth
  reconciliation.
- `docs/AUTHORIZATION_MODEL.md` — authorization and safety model.
- `docs/EXECUTION-SEMANTICS.md` — retries, cancellation, idempotency,
  timeouts and resource limits.
- `docs/GATEWAY-INTEGRATION-TEST-MATRIX.md` — external gateway test
  matrix and adversarial verification.
- `docs/RELEASE_PROCESS.md` — canonical release procedure.
- `docs/RELEASE_READINESS_v0.1.0.md` — release evidence record.
- `docs/PRODUCTION-DOCUMENTATION-RECONCILIATION.md` — current
  documentation/source-of-truth reconciliation record.

## Status

The original architecture issues (#1–#7) are implemented. Subsequent
production-readiness work has hardened configuration, CLI contracts,
packaging, diagnostics, lifecycle handling, resource portability,
authoritative runit state normalization, execution semantics, ecosystem
adapter contracts, gateway integration, acceptance testing, release
readiness, and CI acceptance gating.

Yasin-Operations `v0.1.0` is a repository-local standalone release
candidate/readiness state. This statement is **not** an ecosystem-wide
architecture certification. YASIN-DOCS remains the architectural source
of truth for cross-project status and must be reconciled independently.

It does not require any target Yasin repository for core operation.
