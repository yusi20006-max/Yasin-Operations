# Yasin-Operations runbook

Operational notes for the standalone Operations component. This document does
not replace YASIN-DOCS architecture authority.

## Local commands

```sh
python -m yasin_operations doctor
python -m yasin_operations status
python -m yasin_operations health
python -m yasin_operations monitor
python -m yasin_operations restart <service> --dry-run
python -m yasin_operations restart <service> --confirm
yasin-operations --version
```

Use `--json` for machine-readable output.

## Single-command service startup contract

Every Yasin service that exposes a local listening port should provide one
canonical startup entrypoint. The entrypoint is responsible for preflight and
recovery so the operator does not need a separate `kill` step.

Required behavior:

1. Determine the configured service port (using the service default when no
   override is supplied).
2. If the port is free, start the service.
3. If the port is occupied, identify the process holding it before taking any
   action.
4. If the process is positively identified as a previous instance owned by the
   same Yasin service, terminate it gracefully, verify that it exits, verify
   that the port is released, and then start a fresh instance.
5. If the process is another or unrecognized program, fail closed: report the
   port, PID/process identity when available, and do not kill or modify it.
6. Never treat a successful `kill` request alone as proof of recovery; startup
   must verify both process termination and port release before launching the
   replacement instance.

This contract applies across Yasin services, including Openfeed, and is the
preferred Termux/Android operator experience: one startup command should be
safe to repeat.

## Production acceptance

Hosted/offline acceptance:

```sh
python scripts/production_acceptance.py
python scripts/production_acceptance.py --json
```

Live service inspection is opt-in and remains read-only:

```sh
python scripts/production_acceptance.py --live
python scripts/production_acceptance.py --live --json
```

See `docs/TERMUX-LIVE-ACCEPTANCE.md` for PASS/FAIL/SKIP/BLOCKED classification,
optional-service handling, and Termux operator commands.

A runit result beginning with `run:` is interpreted as actual `running`. A result beginning with `down:` is actual `stopped`, even when the text says `normally up`. `fail:` and `timeout:` are actual `failed`. Desired state is not substituted for actual state. Therefore a service configured as desired `running` but reported by runit as `down: ... normally up` is a genuine runtime failure for a live acceptance run, not a harness success.

Use `--json` for machine-readable harness output.

## Release readiness

Before a release candidate, run:

```sh
python scripts/release_readiness.py --json
```

This is a safe, non-destructive gate. It verifies that the authoritative package version is present, tracked repository files contain no forbidden credential/key/cache artifacts, the source tree has no imports of external Yasin packages, and the canonical acceptance harness succeeds.

The package can be verified independently with:

```sh
python -m pip install build
python -m build --wheel --sdist
python -m pip install dist/*.whl
python -m yasin_operations --version
yasin-operations --version
```

The two version commands must report the same package version. The source distribution must also install successfully in a clean environment.

## Safety rules

- Read-only operations do not require confirmation.
- Mutating operations require explicit confirmation by default.
- Protected targets remain denied unless explicitly allowlisted in policy.
- Dry-run never invokes the target tool.
- All adapter-driven mutations pass through `Executor` and `SafetyPolicy`.
- Audit records contain operation, target, actor/source, correlation ID, result, and timing.
- A service startup launcher may terminate only a process it can positively identify as the same managed service; unknown/foreign processes are fail-closed.

## Failure isolation

If Operations is unavailable, adapters return structured `unavailable_dependency` responses. Existing services are not managed by a shared Operations process and therefore remain independently restartable by their own supervisor.

If a target service fails, the Operations adapter reports the failure; it does not rewrite the target service definition or its configured interval.

## Recovery matrix

| Scenario | Expected behavior |
| --- | --- |
| Operations stopped | Existing services continue independently |
| Operations restarted | Adapter/runtime state is rebuilt from configuration |
| Target service stopped | Status/health reports stopped or unhealthy |
| Target service failed | Status/health reports failed; other services remain observable |
| Optional service directory absent | Live acceptance SKIP; not a product FAIL |
| Service root / sv missing | Live acceptance BLOCKED (environment) |
| Service port free | Single-command launcher starts the service |
| Port held by same managed service | Launcher safely terminates the owned instance, verifies release, then restarts |
| Port held by another service | Launcher fails closed and reports the conflict without killing the other service |

## Universal self-healing startup contract (YasinHub Control Plane)

Authority: YasinHub is the single Control Plane and lifecycle authority for
every managed Yasin service. The lifecycle path is always:

```text
PWA -> YasinHub -> Runit -> Service
```

Runit (`termux-services`) remains the process supervisor for Runit-managed
services. YasinHub orchestrates it via `sv up` / `sv down`; no second
lifecycle manager exists, and Runit-managed services are never bypassed with
ad-hoc background processes. Canonical implementation: `yasinhub/startup.py`
(Hub itself, port 7000), `yasinhub/service_lifecycle.py` (generic contract
for all managed services), `yasinhub/runit.py` (sv adapter),
`yasinhub/service_manager.py` (spawn/stop/restart authority),
`yasinhub/ports.py` (canonical port allocation 7000-7099).

Flow:

```text
Port free
    |
    v
Start through Runit (sv up when Runit-managed, else spawn)
    |
    v
Verify PID + process identity + listening port (+ health where contracted)

Port occupied
    |
    v
Identify owner (PID + real process identity, never port number alone)
    |
    v
Same service?
   |-- YES -> graceful stop via Runit/service lifecycle (SIGTERM, never
   |           blind kill -9) -> wait for process death -> wait for port
   |           release -> start -> verify new PID/identity/port
   |-- NO  -> FAIL CLOSED -> report -> do not kill
```

Rules:

- **Port free**: start normally, then accept RUNNING only with a live PID,
  verified process identity (discovery pattern must match when configured),
  the expected port listening/owned, and the contract health endpoint where
  one is declared.
- **Same-service occupant** (older/stale instance, identity-proven): stop it
  gracefully through the existing Runit/service lifecycle (`sv down` first
  so the supervisor does not resurrect the PID, then SIGTERM). Wait until
  the process actually disappears AND the port is actually released. Then
  start the current instance and verify the new PID, identity, and port.
  The normal path never uses blind `kill -9`; a refusal to stop fails
  closed with no new instance started.
- **Foreign or unknown occupant**: FAIL CLOSED. Do not kill, restart, or
  `kill -9` anything. Do not use port-only ownership assumptions. Report
  the service being started, configured port, occupying PID, safely
  available process identity, ownership classification, and the refusal
  reason. The failure propagates through the YasinHub service
  status/report contract so the PWA displays the real failure.
- **Stale/dead/incomplete metadata** (missing, dead, unreadable, or
  ambiguous PID/process information): treat ownership as unsafe, kill
  nothing, fail safely with the reason reported.
- **Hardened platforms** (e.g. Termux kernels without `/proc/net/tcp`):
  PID-level owner discovery may be unavailable. The contract then
  correlates via a live identity-verified candidate (PID file + pattern
  hints, optional `lsof`/`fuser` listener hints) plus the succeeding
  contract health anchor. Without both, it fails closed.
- **PWA lifecycle**: Start/Stop/Restart/Status operate on real services
  through YasinHub/Runit and return real PID, process identity, port
  state, service state, and failure reasons. No display-only state.
- **Execution**: Termux / Android ARM64, non-interactive. No prompts, no
  stdin reads, no secrets in logs or reports.
