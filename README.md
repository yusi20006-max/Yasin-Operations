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

## Termux / runit

The optional always-on service definition is under
`deploy/termux/runit/yasin-operations/`. It runs the standalone daemon
under `runit`; it does not modify existing Hermes, Yasin-AI, YasinPress,
or YasinRelay service definitions.

Runtime configuration is environment-backed, including the runit
service root, `sv` path, registered service names, execution timeout,
and health interval.

## Verification

The repository includes unit, integration, safety, adapter, CLI,
resource, and failure-isolation tests. GitHub Actions runs the full
suite on Python 3.11 through 3.14.

See `docs/OPERATIONS-RUNBOOK.md` for the production/operator workflow.

## Status

Issues #1 through #7 are implemented on `main` after their respective
pull requests. The repository is now at the production-integration
stage; no target Yasin repository is required for standalone operation.
