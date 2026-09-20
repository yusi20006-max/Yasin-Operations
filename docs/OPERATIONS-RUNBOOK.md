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

## Termux named launchers

Issue #206 provides one registry-backed launcher layer for Termux/Android
ARM64. Install from the canonical Operations checkout:

```sh
cd ~/yasineco/Yasin-Operations
bash scripts/install-termux-launchers.sh
yasin-launch list
```

The installer creates canonical commands in `~/.local/bin`, including
`opencode`, `codex`, `claude`, `yasin`, `yasinhub`, `yasin-agent`,
`yasinfeed`, `yasinrelay`, `yasin-ai`, `yasinpress`, `yasin-coder`,
`yasin-core`, and `yasin-mcp` when those launchers are present in the registry.
Arguments are forwarded unchanged for direct CLI programs. The registry is
`yasin_operations/termux-launchers.json`; do not create unrelated per-app
aliases outside this registry.

### Launcher ownership contract

For a portful launcher:

1. Determine the canonical port from the registry/authoritative service
   contract.
2. Check the port before starting.
3. If free, start through the configured lifecycle authority and verify the
   resulting service state.
4. If occupied, never assume ownership from the port number alone.
5. For YasinHub-managed services, the launcher delegates the ownership
   decision to `yasin start/restart <service>` -> YasinHub. YasinHub must prove
   same-service ownership before stopping an existing process.
6. A same-service occupant is stopped gracefully through the existing
   lifecycle mechanism, the process death and port release are verified, and a
   fresh instance is started and verified.
7. A foreign, unknown, stale, or ambiguous occupant fails closed. The launcher
   must not kill or modify that process.

For portless CLIs such as `opencode`, no fabricated port is introduced. The
real executable is invoked directly and arguments/exit status are preserved.

### Ownership boundaries

```text
named command
    |
    +--> portless CLI -----------------> real CLI entrypoint
    |
    +--> YasinHub-managed service -----> YasinCLI -> YasinHub -> Runit -> Service
    |
    `--> direct portful service -------> verified identity -> graceful stop -> start
```

The launcher is not a second Control Plane. YasinHub remains the sole
lifecycle authority for Hub-managed services and Runit remains the supervisor
behind it.

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


## YasinCoder 0.2.0 — Termux AI runtime runbook

This section records the verified YasinCoder local/cloud provider setup and
the exact operator commands used during v0.2.0 verification. It is intended
to prevent repeating environment discovery from scratch.

### Canonical checkout and release

Canonical Termux checkout:

```sh
cd ~/YASIN-REPOS/YasinCoder
git status --short
git describe --tags --exact-match HEAD
cat VERSION
```

Verified release state:

- Repository: `yusi20006-max/YasinCoder`
- Branch: `master`
- Release: `v0.2.0`
- Verified HEAD/tag commit: `d8ff87a1b67470c896cb4ddd6e1799518ab68339`
- Native Termux Python: 3.14.6
- Platform acceptance target: Android / Termux ARM64
- Do not use an Ubuntu/proot environment as a substitute for native Termux
  acceptance.

### YasinCoder startup and basic diagnostics

Use the installed `yasincoder` launcher from the canonical checkout:

```sh
cd ~/YASIN-REPOS/YasinCoder

yasincoder help
yasincoder info
yasincoder models
yasincoder doctor
yasincoder project
yasincoder brain
```

Main AI commands:

```sh
cd ~/YASIN-REPOS/YasinCoder

yasincoder chat "<prompt>"
yasincoder plan "<coding task>"
yasincoder autonomous "<coding task>"
yasincoder review "<request>"
yasincoder fix "<request>"
yasincoder refactor "<request>"
yasincoder explain "<request>"
yasincoder testgen report
yasincoder testgen generate
yasincoder testgen run
yasincoder testgen verify
```

There is no supported `yasincoder run` command in v0.2.0; it reports
`Unknown command.`.

### Gemini provider

Gemini is configured through YasinCoder's model registry. The verified setup
uses a user-only key file rather than placing the key in the repository:

```sh
cd ~/YASIN-REPOS/YasinCoder

yasincoder setup gemini
yasincoder models
```

Verified primary Gemini model configuration:

```text
name: gemini
type: gemini
base_url: https://generativelanguage.googleapis.com/v1beta/openai
model: gemini-3.8-flash
api_key_file: ~/.config/yasin-coder/gemini.key
timeout: 120
temperature: 0.2
max_tokens: 4096
```

A second configured Gemini model is:

```text
gemini:gemini-2.5-flash
type: gemini
api_key_env: GEMINI_API_KEY
```

Check the registry without printing the secret:

```sh
cd ~/YASIN-REPOS/YasinCoder
yasincoder models
```

Important reliability finding from repeated live tests: Gemini responses were
intermittent. Three consecutive provider tests produced failure, success,
failure; observed failures surfaced as `RoutingError: No provider succeeded`
and the successful request returned the requested test token. Therefore a
Gemini `No provider succeeded` event must not automatically be interpreted as
a YasinCoder code defect.

### Local Qwen3-1.7B provider

Verified model:

```text
~/models/qwen3-1.7b/Qwen3-1.7B-Q4_K_M.gguf
```

Canonical llama-server binary:

```text
/data/data/com.termux/files/usr/bin/llama-server
```

YasinCoder's discovered local registry entry is:

```text
llama_cpp:/data/data/com.termux/files/home/models/qwen3-1.7b/Qwen3-1.7B-Q4_K_M.gguf
type=llama_cpp
base_url=http://127.0.0.1:18080
offline=True
```

Start the local server with the verified lightweight Termux settings:

```sh
cd ~/YASIN-REPOS/YasinCoder

MODEL="$HOME/models/qwen3-1.7b/Qwen3-1.7B-Q4_K_M.gguf"

nohup llama-server \
  -m "$MODEL" \
  --host 127.0.0.1 \
  --port 18080 \
  -c 2048 \
  -np 1 \
  -t 4 \
  >"$HOME/qwen3-1.7b-server.log" 2>&1 &

sleep 2
curl -fsS http://127.0.0.1:18080/health
```

Expected health response:

```text
{"status":"ok"}
```

Direct server smoke test:

```sh
cd ~/YASIN-REPOS/YasinCoder

curl -fsS http://127.0.0.1:18080/completion \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Reply with exactly: QWEN_DIRECT_OK","temperature":0,"n_predict":8,"cache_prompt":false}'
```

The model is functional even if a very short generation can truncate or
continue unexpectedly. The verified server log showed successful prompt and
generation evaluation at roughly 6 tokens/second generation speed.

### Verified YasinCoder -> Qwen smoke test

Force the local model for one invocation without changing the persistent
default model:

```sh
cd ~/YASIN-REPOS/YasinCoder

YASIN_MODEL="llama_cpp:/data/data/com.termux/files/home/models/qwen3-1.7b/Qwen3-1.7B-Q4_K_M.gguf" \
YASIN_LLAMA_MAX_TOKENS=128 \
yasincoder chat "You are testing YasinCoder on a local Qwen model. Reply with exactly: YASINCODER_QWEN_OK"
```

Verified output:

```text
YASINCODER_QWEN_OK
```

This proves the complete local path:
`yasincoder -> AIClient -> ProviderManager -> Router ->
LlamaCppAdapter -> llama-server -> Qwen3-1.7B`.

### Verified structured JSON smoke test

Use this to confirm that Qwen can produce a simple valid JSON response through
YasinCoder:

```sh
cd ~/YASIN-REPOS/YasinCoder

YASIN_MODEL="llama_cpp:/data/data/com.termux/files/home/models/qwen3-1.7b/Qwen3-1.7B-Q4_K_M.gguf" \
YASIN_LLAMA_MAX_TOKENS=512 \
yasincoder chat 'Return ONLY valid JSON: {"steps":[{"description":"inspect ModelManager.default"}]}'
```

Verified output:

```json
{"steps":[{"description":"inspect ModelManager.default"}]}
```

### Planner test findings

The following real planner invocation was attempted:

```sh
cd ~/YASIN-REPOS/YasinCoder

YASIN_MODEL="llama_cpp:/data/data/com.termux/files/home/models/qwen3-1.7b/Qwen3-1.7B-Q4_K_M.gguf" \
YASIN_LLAMA_MAX_TOKENS=512 \
yasincoder plan "Inspect the YasinCoder repository. Add one focused pytest regression test that verifies ModelManager.default() respects the YASIN_MODEL environment variable when it names an existing configured model. Do not modify production code. Run the focused test and report the result."
```

Observed result:

```text
routing.RoutingError: No provider succeeded
```

A simpler JSON request immediately succeeded, so this result does not prove that
the local provider is broken. The next diagnostic step is to inspect the exact
Planner prompt and `validate_plan()` schema before changing production code.

### Important local-provider behavior

YasinCoder reads `YASIN_MODEL` from the environment for a per-process model
override. A configured local `llama_cpp` model is marked `offline=True`, so
the router isolates it rather than falling back to Gemini.

The lightweight llama-server configuration above is important on this
Termux/Android device. An earlier configuration using `-c 8192` and four
parallel slots caused completion requests to time out. Reducing to
`-c 2048 -np 1 -t 4` produced a successful health check and completion.

Do not expose or commit `~/.config/yasin-coder/gemini.key`. Keep credentials
outside repositories and avoid printing their contents in diagnostics.
