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

### YasinCoder lifecycle boundary

YasinCoder is a CLI/project workflow, not a daemon or service:

- Repository: `yusi20006-max/YasinCoder`, branch `master`
- Canonical path: `~/YASIN-REPOS/YasinCoder` (outside `~/yasineco`)
- Install: `python -m pip install .` (dev: `python -m pip install -e .`)
- Test: `python -m unittest discover -s tests -p 'test_*.py' -v`
- Entry points: `yasincoder`, `yasincoder-tui` (console scripts; no ports)
- It MUST NOT be added to the YasinHub/Runit managed-service lifecycle.
- It MUST NOT be confused with the retired Hub service name `yasin-coder`,
  nor with OpenCode, Claude Code, or Codex, which are not Yasin runtime
  services.


## API Token Manager PWA — v1.0.0 execution runbook

Repository: `yusi20006-max/api-token-manager-pwa`  
Release: `v1.0.0`  
Final commit: `a00e8fcbe4f6345ee762173086b4d67110080cdd`

This project is a static PWA. It does not have a dedicated bundler, build server, or application backend. The following commands are the verified Termux/Android operator path.

### Canonical checkout

`bash
cd ~/api-token-manager-pwa
git fetch origin
git checkout main
git pull --ff-only origin main
git status --short
`

The final release state must be clean before acceptance.

### Local PWA startup

Use a free local HTTP port:

`bash
cd ~/api-token-manager-pwa
python -m http.server 8090
`

Open:

`text
http://127.0.0.1:8090/
`

The Python server only serves static files. It is not an API backend.

Do not reuse a port already occupied by another local application. During v1.0.0 acceptance, port `8080` was also used by OpenFeed traffic; requests such as `/api/status` and `/api/image` therefore reached the static server and returned 404. This was an environment/port collision, not an API Token Manager PWA defect. Port `8090` was used for the successful local acceptance.

### Node regression

`bash
cd ~/api-token-manager-pwa
npm test
`

Verified v1.0.0 result:

`text
60/60 tests passed
`

### Browser/PWA regression

The authoritative browser suite is the GitHub Actions workflow, which runs on Ubuntu with Chromium:

`bash
npm install
npx playwright install chromium
npx playwright test
`

The suite covers PWA boot, delegated UI, reset/storage isolation, and Service Worker API-cache isolation. It uses test fixtures and does not require real provider credentials.

#### Native Termux limitation

Native Android/Termux execution of Playwright Chromium is not supported by the installed Playwright platform path. The following command failed with:

`text
Unsupported platform: android
`

`bash
npx playwright install chromium
npx playwright test
`

Therefore native Termux browser execution is classified as an environment limitation, not a product failure. The Browser/PWA GitHub Actions workflow passed for the final commit.

### Dependency installation finding

`npm ci` is not a valid installation command for this repository's current release because no `package-lock.json` is tracked.

Use:

`bash
cd ~/api-token-manager-pwa
npm install
`

Local `node_modules/` and generated `package-lock.json` were removed after testing and were not committed to v1.0.0.

### GitHub Pages

GitHub Pages is the hosted deployment path. Deployment status is verified through the repository's GitHub Actions Pages workflow.

### Release verification

`bash
cd ~/api-token-manager-pwa
git fetch origin --tags
git checkout main
git pull --ff-only origin main
git describe --tags --exact-match HEAD
gh release view v1.0.0 --repo yusi20006-max/api-token-manager-pwa
`

Expected tag:

`text
v1.0.0
`

### Runtime/security contracts recorded in v1.0.0

- Service Worker caches static same-origin assets only; provider API request/response data is not cached.
- Google Gemini authentication uses `x-goog-api-key` and does not place the API key in the request URL.
- Browser-ambiguous fetch failures remain `NETWORK_ERROR` unless explicit evidence supports `CORS_BLOCKED`.
- Smart Setup keeps discovery and health evidence separate and reports `CONFLICTING_EVIDENCE` when evidence conflicts.
- Reset clears managed API/session state without clearing unrelated local storage.
- Capability Matrix does not infer inference support from `/models` alone.
- OrcaRouter runtime smoke coverage verifies `/models`, `/chat/completions`, and `/responses` using mocked HTTP fixtures.
- No real provider credentials are required by the regression suite.

### v1.0.0 implementation history

The final gap/regression audit was resolved through the following merged issues and PRs:

| Issue | Scope | PR | Result |
| --- | --- | --- | --- |
| #35 | Service Worker / API cache isolation | #45 | Merged |
| #36 | CORS runtime contract | #46 | Merged |
| #37 | Google header authentication | #47 | Merged |
| #38 | Remove obsolete Phase 6 automation | #48 | Merged |
| #49 | Smart Setup alignment | #50 | Merged |
| #39 | Smart Setup auth evidence | #51 | Merged |
| #40 | Reset single invocation | #52 | Merged |
| #41 | Separate UI from storage | #53 | Merged |
| #42 | Browser/PWA regression suite | #54 | Merged |
| #43 | Provider/runtime documentation | #55 | Merged |
| #44 | OrcaRouter runtime smoke | #56 | Merged |

Final acceptance:

`text
Node tests: 60/60 PASS
Browser/PWA CI: PASS
GitHub Pages: PASS
Local PWA on Termux: PASS
Native Termux Playwright: BLOCKED (Android unsupported)
Release v1.0.0: PASS
`

The project README contains the user-facing execution and troubleshooting record; YASIN-DOCS contains the system-level project record.

## Yasin System Release

Issue #216 establishes a system-level release contract for the coordinated Yasin ecosystem. A system release is a reproducible snapshot of multiple repositories; individual repository releases remain owned by their respective repositories.

### Whole-system bootstrap (Issue #218)

Two modes, never mixed:

- **Mode A — current `main`/`master` bootstrap.** Synchronize every active
  repository with its origin branch. The reusable procedure is
  `scripts/bootstrap-system.sh` (sync existing checkouts) or
  `scripts/bootstrap-system.sh --clone` (fresh clone, skips existing
  directories). The script fails fast and never resets, rebases, cleans,
  or force-pushes; dirty trees and local commits are reported, not destroyed.
- **Mode B — exact system-release reproduction.** Check out the immutable
  40-character commit SHAs recorded in the release manifest instead of
  branch tips. Never rely on tags alone.

Explicit branch map (15 active repositories). Every repository uses `main`
except YasinCoder, which uses `master`:

```text
~/yasineco: Openfeed, YASIN-DOCS, Yasin-AI, Yasin-MCP, Yasin-Operations,
  Yasin-agent, Yasin-cli, Yasin-core, YasinHub, YasinPress-Rewrite-,
  YasinRelay, Yasinfeed, api-token-manager-pwa, YasinPress  -> main
~/YASIN-REPOS/YasinCoder                                        -> master
```

### v1.0.0 verified baseline

The first baseline is recorded in `releases/YASIN-SYSTEM-v1.0.0.json`. It contains the exact `main` commit SHA for 14 included repositories plus synchronization, runtime, shutdown, and limitation evidence.

The 2026-09-22 verification recorded 14 repositories synchronized to origin (0 ahead / 0 behind), zero tracked changes, PASS runtime verification for applicable services, and PASS graceful shutdown. Yasin-MCP is explicitly PASS WITH LIMITATIONS because live stdio was blocked by the missing MCP SDK in native Termux. YasinCoder is retired/excluded and the dated YasinHub backup checkout is excluded.

### Creating a future system release

From the canonical native Termux ecosystem root:

```sh
cd ~/yasineco

# Synchronize every included repository with origin/main and record full SHAs.
# Run the canonical runtime verification from Yasin-Operations.
# Stop test-started services and verify ports/processes are released.

cd ~/yasineco/Yasin-Operations
python scripts/validate_system_release.py releases/YASIN-SYSTEM-v<version>.json
```

The manifest is the source of truth for the coordinated snapshot. A public system tag/release artifact is created only after final verification. Never promote SKIP or BLOCKED checks to PASS, and do not include retired repositories or backup checkouts without an explicit scope change.

Future system releases after v1.0.0 include YasinCoder (branch `master`,
exact SHA recorded at verification time) under Issue #218. The historical
`releases/YASIN-SYSTEM-v1.0.0.json` artifact is frozen and MUST NOT be
rewritten to add it.


## Android APK build on Termux/ARM64 — reusable Yasin Chess procedure

This section records the verified Android APK build procedure established on
Yasin Chess v0.3.0 on native Termux/Android ARM64. Reuse this procedure for
future Android applications when the host is ARM64 and the official Android
Build Tools binaries are x86_64.

### Scope and verified environment

- Host: Android / Termux ARM64 (aarch64), native Termux; do not substitute
  Ubuntu/proot for Android acceptance.
- Java: OpenJDK 21.
- Gradle wrapper: use the project's wrapper.
- Android SDK root:
  `~/android-sdk`
- SDK platform used by Yasin Chess:
  `platforms/android-36`
- Build Tools:
  `build-tools/35.0.0`
- Box64:
  `box64-glibc 0.4.4`, executed through `glibc-runner`.
- Project:
  `~/YASIN-REPOS/yasin-chess`
- Capacitor Android:
  `@capacitor/core`, `@capacitor/android`, and `@capacitor/cli` 8.5.2.
- Android project configuration:
  `minSdkVersion=24`, `compileSdkVersion=36`,
  `targetSdkVersion=36`.

### Important architecture finding

The official Android Build Tools package used here contains x86-64 native
executables. On aarch64 Termux, direct execution fails with `Exec format
error`. Box64 provides the x86-64 compatibility layer.

The verified Box64 executable is:

```text
/data/data/com.termux/files/usr/glibc/bin/box64
```

It must be invoked through the verified Termux glibc runner:

```sh
glibc-runner --shell "$BOX64" --version
```

Expected result includes:

```text
Box64 arm64 v0.4.4
```

Do not assume `command -v box64` succeeds. On this environment the binary
was present under the glibc prefix and direct execution was not the valid path.

### SDK package acquisition

Keep downloaded SDK archives separate from the installed SDK tree. For this
verified procedure the archives were downloaded externally with Android
Download Manager, copied into:

```text
~/android-sdk/downloads/
```

Verified archive:

```text
commandlinetools-linux-15859902_latest.zip
```

Its SHA256 was verified before extraction:

```text
4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583
```

The Build Tools archive used was:

```text
build-tools_r35_linux.zip
```

Verified SHA256:

```text
bd3a4966912eb8b30ed0d00b0cda6b6543b949d5ffe00bea54c04c81e1561d88
```

The archive extracted to a directory named `android-15`, but its
`source.properties` reported `Pkg.Revision=35.0.0`. The extracted
directory was therefore installed as:

```text
~/android-sdk/build-tools/35.0.0
```

The archive is retained in `~/android-sdk/downloads/` for reproducibility.

The Android platform archive used was:

```text
platform-36_r02.zip
```

Its installed target is:

```text
~/android-sdk/platforms/android-36
```

Do not rely on guessed Google repository filenames. If automatic
`sdkmanager` installation is unreliable on Termux, acquire the exact
official archives separately, verify their checksums, then install them into
the SDK tree.

### Verify the Build Tools before building

Confirm the package metadata and important executables:

```sh
cd ~/YASIN-REPOS/yasin-chess

cat "$HOME/android-sdk/build-tools/35.0.0/source.properties"

ls -lh "$HOME/android-sdk/build-tools/35.0.0/"{aapt,aapt2,aidl,apksigner,d8,zipalign}
```

The metadata must identify Build Tools 35.0.0.

Test AAPT2 through Box64:

```sh
cd ~/YASIN-REPOS/yasin-chess

BOX64="$PREFIX/glibc/bin/box64"
AAPT2="$HOME/android-sdk/build-tools/35.0.0/aapt2"

glibc-runner --shell "$BOX64" "$AAPT2" version
```

A successful response identifies Android Asset Packaging Tool 2.x. Direct
execution of the same x86-64 `aapt2` binary is expected to fail on aarch64.

### Capacitor/Gradle preparation

Use the project's existing Gradle wrapper and Android project. Do not replace
the wrapper with a system Gradle installation.

For the Yasin Chess build, the local TypeScript 7 package was incompatible
with the Termux/Android ARM64 environment because the package attempted to
load `@typescript/typescript-android-arm64`. A clean dependency install plus
a local no-save TypeScript 5.9.3 override produced the verified web build.

The Android build therefore used the project's normal dependencies with:

```sh
cd ~/YASIN-REPOS/yasin-chess

npm install --no-save --force typescript@5.9.3
npm run build
```

Keep generated `node_modules/`, `dist/`, and other local build artifacts
out of Git unless the repository explicitly tracks them.

### AAPT2 override for Gradle

Create a small wrapper so Gradle can invoke the x86-64 AAPT2 through Box64:

```sh
cd ~/YASIN-REPOS/yasin-chess

mkdir -p "$HOME/android-sdk/aapt2-box64"

cat > "$HOME/android-sdk/aapt2-box64/aapt2" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
exec glibc-runner --shell "$HOME/android-sdk/../usr/glibc/bin/box64" "$HOME/android-sdk/build-tools/35.0.0/aapt2" "$@"
EOF

chmod +x "$HOME/android-sdk/aapt2-box64/aapt2"
```

The Gradle property that selects this wrapper is:

```text
-Pandroid.aapt2FromMavenOverride=$HOME/android-sdk/aapt2-box64/aapt2
```

This is the key reusable technique for Android builds whose AAPT2 binary is
x86-64 while the host is ARM64.

### Verified Yasin Chess APK build

The verified native Termux build command was:

```sh
cd ~/YASIN-REPOS/yasin-chess

AAPT2_WRAPPER="$HOME/android-sdk/aapt2-box64/aapt2"

./gradlew assembleDebug --no-daemon \
  -Pandroid.aapt2FromMavenOverride="$AAPT2_WRAPPER"
```

Verified result:

```text
BUILD SUCCESSFUL
243 actionable tasks: 173 executed, 70 up-to-date
```

APK output:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

Verified APK size:

```text
4237990 bytes
```

Verified SHA256:

```text
3abfd4dc4a9e0dd712e6b1cc5153a2228a5f9d7ee8e6b5492a9275d6f006107a
```

Always record the final APK SHA256 after a successful build.

### APK installation on the same Android device

Native Termux `adb` initially failed because the installed
`android-tools 37.0.0-2` was paired with older `libc++ 29` and
`ndk-sysroot 29-2`. The targeted dependency upgrade fixed ADB:

```sh
apt-get install -y libc++ ndk-sysroot
adb --version
adb devices -l
```

Verified versions:

```text
libc++ 30
ndk-sysroot 30
android-tools 37.0.0-2
```

Wireless ADB pairing from Termux to the same Android device was not successful
in this environment. Repeated `adb pair` attempts returned:

```text
error: protocol fault (couldn't read status message): Success
```

Direct `adb connect` to the Wireless Debugging connection port also failed.
Do not treat that failure as an APK-build failure.

For installation on the same device, the verified fallback is to invoke the
Android package installer through Termux:

```sh
cd ~/YASIN-REPOS/yasin-chess

APK="$PWD/android/app/build/outputs/apk/debug/app-debug.apk"
termux-open "$APK"
```

The Yasin Chess v0.3.0 debug APK was successfully installed on the physical
Android device using this path.

### Android runtime acceptance

APK installation success is not runtime acceptance. After installation,
open the application on the physical device and test at minimum:

1. Application cold start without crash.
2. Board renders with all 64 cells equal and square.
3. Pieces render consistently inside their cells.
4. A legal player move executes.
5. Offline opponent response executes.
6. Online opponent response executes when the online path is configured.
7. UI controls operate.
8. Game state survives application close and cold reopen.
9. Offline behavior remains usable without network access.
10. No unexpected state reset occurs after reload/restart.

Record runtime defects separately from build/install defects. In the first
Yasin Chess v0.3.0 physical-device test, installation succeeded but runtime
acceptance found opponent-response failures in both offline and online modes,
non-uniform board-cell sizing, non-standard piece artwork, and loss of game
state after application restart.

### Reuse checklist for future Android projects

```text
[ ] Confirm aarch64 Android/Termux and Java 21
[ ] Set ANDROID_SDK_ROOT / SDK path
[ ] Keep downloaded SDK archives under ~/android-sdk/downloads/
[ ] Verify archive SHA256 before extraction
[ ] Install platform and Build Tools into the SDK tree
[ ] Confirm Build Tools source.properties
[ ] Confirm x86-64 AAPT2 architecture when applicable
[ ] Verify Box64 through glibc-runner
[ ] Create/use the AAPT2 Box64 wrapper
[ ] Run the project's web build
[ ] Run Gradle through the project wrapper
[ ] Pass android.aapt2FromMavenOverride to Gradle
[ ] Record APK path, size, and SHA256
[ ] Upgrade only required Termux dependencies when ADB has ABI mismatch
[ ] Prefer termux-open APK installation when same-device ADB is unavailable
[ ] Perform physical-device runtime acceptance separately
[ ] Do not mark Android release acceptance PASS from build/install alone
```


### Future-project adaptation rules

The procedure above is the canonical **method**, not a requirement that every future application use the same versions. For a new Android project:

1. Inspect the project's required Android Gradle Plugin, Gradle wrapper, compile SDK, target SDK, min SDK, Java version, and Capacitor/Cordova/native stack before changing anything.
2. Reuse the existing SDK root and installed platform/build-tools when they satisfy those requirements. Do not redownload a package that is already verified and compatible.
3. If the new project requires another SDK platform or Build Tools version, download that exact official archive, verify its SHA256, retain the archive under `~/android-sdk/downloads/`, and install it beside the existing versions. Never replace a working version blindly.
4. Check the architecture of every native Android tool that Gradle must execute. If an x86-64 tool is required on aarch64, prefer the verified `glibc-runner -> Box64` path rather than copying or modifying binaries.
5. Re-test AAPT2 directly through the wrapper before invoking a full Gradle build. If AAPT2 is native ARM64 in a future toolchain, the Box64 override is unnecessary.
6. Prefer the project's Gradle wrapper. Do not globally upgrade Gradle or AGP merely to make a build pass.
7. Keep project-specific workarounds local and documented. A TypeScript compatibility override used by one project must not be copied to another project without reproducing the compatibility failure.
8. Build first with `assembleDebug`. Only after debug build and physical runtime acceptance are green should release APK/AAB signing and release packaging be attempted.

### Reusable verification commands

The following checks are intentionally project-neutral except for the checkout path:

```sh
cd <ANDROID_PROJECT>

echo "=== HOST ==="
uname -m
java -version
node --version
npm --version

echo "=== SDK ==="
echo "ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT:-$HOME/android-sdk}"
ls -ld "$HOME/android-sdk/platforms" "$HOME/android-sdk/build-tools"

echo "=== BOX64 ==="
BOX64="$PREFIX/glibc/bin/box64"
glibc-runner --shell "$BOX64" --version

echo "=== BUILD TOOLS ==="
cat "$HOME/android-sdk/build-tools/<BUILD_TOOLS_VERSION>/source.properties"

echo "=== AAPT2 ==="
AAPT2="$HOME/android-sdk/build-tools/<BUILD_TOOLS_VERSION>/aapt2"
glibc-runner --shell "$BOX64" "$AAPT2" version

echo "=== PROJECT ==="
git status --short
git rev-parse --show-toplevel
```

Replace placeholders before execution. Do not paste the placeholder commands unchanged into an acceptance run.

### Artifact acceptance commands

After a successful build, record the exact artifact rather than relying on a directory listing:

```sh
cd <ANDROID_PROJECT>

APK="$PWD/<APK_PATH>"

test -f "$APK"
ls -lh "$APK"
sha256sum "$APK"
```

The SHA256 belongs in the build report. If the APK is rebuilt, the new hash must be recorded; never carry forward a hash from an older build.

### Release signing boundary

Debug APK generation and release signing are separate stages.

- Debug APK: suitable for local installation and runtime smoke testing.
- Signed release APK: requires the project's release signing architecture and secrets; keystore material must never be committed to Git.
- AAB: build only after the release configuration is verified.
- Production release: requires clean repository state, CI/release workflow verification, signing verification, artifact hashes, and physical-device acceptance appropriate to the release scope.

For Yasin Chess, release signing is documented separately in `docs/ANDROID-SIGNING.md`. The Termux build procedure must not embed signing passwords, aliases, keystore files, or base64 secrets.

### Troubleshooting decision tree

```text
Gradle fails before AAPT2
    -> inspect Java / Gradle wrapper / AGP / dependency compatibility

AAPT2: Exec format error
    -> verify host is aarch64
    -> verify AAPT2 is x86-64
    -> verify Box64 through glibc-runner
    -> use android.aapt2FromMavenOverride

Box64 itself does not start
    -> do not replace AAPT2
    -> verify glibc-runner and the actual Box64 path
    -> stop and diagnose the runtime first

ADB cannot start with a libc++ symbol error
    -> inspect android-tools dependency versions
    -> simulate the targeted libc++/ndk-sysroot upgrade
    -> upgrade only the required dependencies
    -> re-run adb --version

ADB Wireless Pairing fails
    -> record the exact adb error
    -> do not classify APK build as failed
    -> try direct connection only with Android's displayed connection port
    -> if same-device wireless ADB remains unavailable, use termux-open

APK installs but app fails at runtime
    -> classify as runtime acceptance failure, not build failure
    -> reproduce on physical device
    -> capture logs/evidence
    -> create an issue against the application layer

APK builds and installs but state resets after restart
    -> classify as persistence/runtime regression
    -> inspect storage hydration and lifecycle handling

UI is distorted on device but web build passes
    -> classify as Android/runtime UI regression
    -> inspect viewport, safe-area, CSS sizing, and native WebView behavior
```

### Evidence and reporting standard

Every Android build report should contain:

- project/repository and commit SHA;
- Android/Termux architecture;
- Java, Node, Gradle/AGP and relevant SDK versions;
- exact Build Tools version;
- whether AAPT2 was native or executed through Box64;
- build command;
- Gradle result and duration when useful;
- APK/AAB path;
- artifact size;
- SHA256;
- installation method and result;
- physical-device runtime result;
- known failures/limitations;
- whether the result is **BUILD PASS**, **INSTALL PASS**, **RUNTIME PASS**, or **RELEASE PASS**.

Never collapse these states into a single "APK works" statement.

### Canonical build pattern

The reusable pattern is:

```text
Android source
    |
    v
npm dependencies / web build
    |
    v
Gradle wrapper
    |
    +--> x86-64 AAPT2
    |       |
    |       v
    |    glibc-runner -> Box64 -> AAPT2
    |
    v
Debug/Release APK
    |
    +--> SHA256 verification
    |
    +--> physical Android installation
    |
    \`--> runtime acceptance
```

For future projects, preserve this separation:

- **Build success** = Gradle produced the APK.
- **Artifact verification** = APK path, size, and SHA256 recorded.
- **Installation success** = Android package installer accepted the APK.
- **Runtime acceptance** = application behavior verified on the physical device.
- **Release acceptance** = runtime acceptance plus project-specific security,
  signing, regression, and release checks.
