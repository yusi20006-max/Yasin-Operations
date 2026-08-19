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

## Production acceptance and release readiness

The canonical read-only acceptance harness is:

```sh
python scripts/production_acceptance.py
python scripts/production_acceptance.py --live
```

The first command is safe for normal CI and skips live runit inspection.
The `--live` form adds read-only `sv status` checks. No lifecycle mutation
is performed by either form.

Release-readiness checks are available with:

```sh
python scripts/release_readiness.py --json
```

This verifies the authoritative version, repository hygiene, independence
from external Yasin package imports, and the safe acceptance surface.

## Verification

The repository includes unit, integration, safety, adapter, CLI,
gateway, resource, release-readiness, and failure-isolation tests. GitHub
Actions runs the full suite on Python 3.11 through 3.14 and separately
builds/tests both wheel and source-distribution artifacts.

See `docs/OPERATIONS-RUNBOOK.md` for the production/operator workflow.

## Status

Issues #1 through #7 are implemented on `main` after their respective
pull requests. The repository is now at the production-integration and
release-hardening stage; no target Yasin repository is required for
standalone operation.
