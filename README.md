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
    mcp_server.py         Optional stdio MCP bridge for Hermes
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
python -m yasin_operations monitor
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

**Transport boundary:** the local JSONL gateway remains the canonical
component-scoped external transport. An optional **stdio MCP bridge**
(`yasin_operations.mcp_server`) is also available for Hermes and other
MCP clients. MCP is never a core dependency; install the optional extra
with `pip install -e ".[mcp]"` or see `requirements-mcp.txt` and
`docs/TERMUX-MCP-COMPATIBILITY.md` for Termux/Python 3.14 notes.
JSONL verification must not be represented as MCP verification, and
MCP verification must not be claimed from JSONL tests alone.

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

Canonical release procedure and readiness evidence:

- `docs/RELEASE_PROCESS.md`
- `docs/RELEASE_READINESS_v0.1.0.md`

The canonical read-only acceptance harness is:

```sh
python scripts/production_acceptance.py
python scripts/production_acceptance.py --json
python scripts/production_acceptance.py --live --json
```

The normal CI workflow covers hosted verification. Live Termux/runit
acceptance remains an operator responsibility on the target device.

## Optional MCP (Hermes)

```sh
pip install -e ".[mcp]"
python -m yasin_operations.mcp_server
```

On Termux Python 3.14 see `docs/TERMUX-MCP-COMPATIBILITY.md`.

An optional stdio MCP bridge is provided for Hermes integration. The
presence of a Hermes CLI alone is not treated as live connectivity evidence;
use the MCP bridge and the documented smoke tests.
