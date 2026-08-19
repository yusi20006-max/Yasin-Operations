# Yasin-Operations

Modular Operations Agent for the Yasin ecosystem.

## Independence

This repository is standalone. It does not require Hermes, Yasin-AI,
YasinPress, YasinRelay, another Yasin repository, an external AI
provider, or a running external service to import and operate its Core.
All integrations are optional adapters around Core contracts.

## Package layout

```
yasin_operations/
    core/             Operations, execution, results
    runtime/          Process/service/health/diagnostics runtime layer
    runtime/termux/   Optional Termux/runit adapter and configuration
    adapters/hermes/  Optional Hermes-facing interface boundary
    adapters/ecosystem/ Optional Yasin service adapters
    safety/           SafetyClass + deny-by-default SafetyPolicy
    logging/          Structured audit trail
    gateway.py        Optional local JSONL Operations Gateway
    gateway_cli.py    Gateway command implementation
    entrypoint.py     Installed CLI router
    cli.py            Standalone operations CLI
    daemon.py         Optional supervised always-on daemon
```

## Safety boundary

Every operation has an explicit `SafetyClass`. Mutations are denied
without explicit confirmation by default. Protected targets, dry-run,
retry limits, timeouts, actor/source attribution, correlation IDs, and
audit records are handled by the Core Executor and SafetyPolicy.
Adapters cannot bypass that boundary.

## CLI

```sh
python -m yasin_operations.cli doctor
python -m yasin_operations.cli status
python -m yasin_operations.cli health
python -m yasin_operations.cli restart <service> --dry-run
python -m yasin_operations.cli restart <service> --confirm
```

Use `--json` for machine-readable output.

### Local Operations Gateway

The optional gateway provides a transport-neutral JSONL interface for
external agents such as Hermes. It uses the existing Hermes operation
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
runtime services, and the repository's standalone operation remain
unchanged when it is not used.

## Production acceptance

The canonical read-only acceptance harness is:

```sh
python scripts/production_acceptance.py
```

Use `--json` for machine-readable results. Use `--live` on a Termux host
to include read-only runit service inspection:

```sh
python scripts/production_acceptance.py --live --json
```

The normal CI workflow runs the non-live acceptance harness on Python
3.11 through 3.14. Live service health is an operator/host verification
step and is not claimed by the hosted CI environment.

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

- `run:` → actual `running` / healthy
- `down:` → actual `stopped`
- `fail:` or `timeout:` → actual `failed`
- unknown status text → actual `unknown`

`desired_state` is separate from actual runtime state. In particular,
`down: ... normally up` means the service is currently stopped even if
runit is configured to keep it supervised.

## Verification

The repository includes unit, integration, safety, adapter, CLI,
gateway, resource, acceptance, and failure-isolation tests. GitHub
Actions runs the full suite and the canonical non-live acceptance
harness on Python 3.11 through 3.14, followed by clean-wheel packaging
verification.

See `docs/OPERATIONS-RUNBOOK.md` for the production/operator workflow.

## Status

The original architecture issues (#1–#7) are implemented. Subsequent
production-readiness work has hardened configuration, CLI contracts,
packaging, diagnostics, service lifecycle handling, resource
portability, authoritative runit state normalization, the production
acceptance harness, and CI acceptance gating.

The repository is in the production-integration stage. Yasin-Operations
remains an optional standalone operations authority and does not require
any target Yasin repository for core operation.
