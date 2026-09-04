# Issue #163 — Implementation

## Branch

`fix/control-plane-startup-verification` (base `main @ 5addef7`), worktree
`~/yasineco/.worktrees/yasinhub-163`.

## Changes

### 1. `yasinhub/service_manager.py` (production)

- `STARTUP_GRACE_SECONDS = 2.0`, `STARTUP_POLL_INTERVAL = 0.2` (documented constants).
- `_wait_for_stable_start(proc)`: bounded poll of `proc.poll()` (fail-fast on early exit;
  attempt-count loop, no `time.time()` arithmetic → mock-compatible).
- `start_service`: replaces single 0.3s check. Early exit → PID removed, FAILED status
  with exit code (`پروسس در حین راه‌اندازی با کد خروج N متوقف شد`), returns False.
  API (`handle_control`) propagates this as `success:false` — the exact false-success
  from the bug report is eliminated at the source.
- `_read_proc_cmdline()` + `verify_process_identity(pid, pattern, start_command)`:
  True (pattern-in-cmdline OR argv[0] match incl. basename fallback), False (foreign),
  None (unverifiable). `/proc`-based → Termux/Android + Linux, no systemd.
- `stop_service`: saved PID equal to Hub's own PID → never kill, drop PID file, skip
  pattern kill. Identity False → warn, drop PID file, skip pattern kill (no blanket kill
  of foreign processes). Otherwise unchanged semantics (verified kill + PID removal).
- Pattern fallback retained for reconciliation/discovery (required by existing tests),
  now with self-PID exclusion; `stop_pid_safely` refuses own PID (defense in depth).
- `restart_service`: verifies old PID dead after stop (else FAILED + False), start
  success, new PID alive, PID differs (else False).

### 2. `yasinhub/adapters/http_transport.py` (production)

- `HttpTransportConfig.from_env`: canonical token-file override applies only when
  `env is None` (real process env). Explicitly injected env mappings are authoritative
  → hermetic tests/callers. Production callers (`build_adapter_from_env()`) unchanged.

### 3. `tests/test_control_plane_startup.py` (new, 7 tests, real processes)

- exit-during-verification → False + PID removed + FAILED status with exit code
  (exact production bug shape; `sleep 1.2; exit 1` — beyond old 0.3s window).
- stable start → True + alive + RUNNING; stop → PID gone + dead + not RUNNING.
- restart → PID differs + old dead + new alive.
- stop never kills Hub's own PID; identity helper unit tests incl. argv[0] ownership.

### 4. `CHANGELOG.md`

- Unreleased entry describing the #163 lifecycle contract.

## Design notes / why safe

- Fresh-spawn verification uses only `proc.poll()` (authoritative for own child) —
  no `is_pid_alive()` on mock PIDs in the success path, so MagicMock-based tests pass.
- Identity refusal cannot false-fire on Hub-spawned children thanks to the argv[0] rule
  (proven by live HTTP verification where pattern ≠ command).
- No new dependencies; no API shape changes; Persian operator messages preserved.
- `relay.db` (untracked, created by test/server runs) left untouched and uncommitted.
