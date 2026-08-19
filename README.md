# Yasin-Operations

Modular Operations Agent for the Yasin ecosystem.

## Independence

This repository is standalone. It does not require Hermes, Yasin-AI,
YasinPress, YasinRelay, another Yasin repository, an external AI
provider, or a running external service to import and operate its Core.
All integrations are optional adapters around Core contracts.

## Package

Current release: `0.1.0`.

Supported Python: `>=3.11`. Hosted CI verifies Python 3.11, 3.12, 3.13,
and 3.14.

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
    version.py        Authoritative package version
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

## Production acceptance and release readiness

The canonical read-only acceptance harness is:

```sh
python scripts/production_acceptance.py
python scripts/production_acceptance.py --json
python scripts/production_acceptance.py --live --json
```

The normal CI workflow runs the non-live acceptance harness on Python
3.11 through 3.14. Live service health is an operator/host verification
step and is not claimed by hosted CI.

Release-readiness checks are available with:

```sh
python scripts/release_readiness.py --json
```

## Verification

The repository includes unit, integration, safety, adapter, CLI,
gateway, resource, release-readiness, acceptance, and failure-isolation
tests. GitHub Actions runs the full suite and canonical non-live
acceptance harness on Python 3.11 through 3.14 and separately builds,
installs, and verifies release artifacts.

See `docs/OPERATIONS-RUNBOOK.md` for the production/operator workflow.
See `docs/RELEASE_READINESS_v0.1.0.md` for the release evidence record.

## Status

The original architecture issues (#1–#7) are implemented. Subsequent
production-readiness work has hardened configuration, CLI contracts,
packaging, diagnostics, lifecycle handling, resource portability,
authoritative runit state normalization, adapter contracts, the
production acceptance harness, release readiness, and CI acceptance
gating.

Yasin-Operations `v0.1.0` is release-ready as an optional standalone
Operations authority. It does not require any target Yasin repository
for core operation.
