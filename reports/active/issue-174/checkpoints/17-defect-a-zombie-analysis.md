# Checkpoint 17 — Zombie False-Success Analysis — Issue #174

**Date:** 2026-09-05 03:03 UTC
**Device:** Samsung SM-A705FN / Android 11 / API 30 / aarch64 arm64-v8a / Termux / Python 3.14.6
**YasinHub HEAD:** 5965c64 (yasineco/YasinHub feat/pwa-glass-control-redesign) — also YasinHub duplicate at ~/YasinHub pwa-dashboard-158 4abf24b
**YasinRelay HEAD:** 6bbe6d4 main
**Yasin-agent HEAD:** 44c130a main
**Yasin-AI HEAD:** 410214d main

## Objective
Determine why Hub reported `success=true` while YasinRelay had already exited / became zombie when SOURCE_CHANNELS empty.

## Traced Path
PWA/API → `yasinhub/api/server.py:handle_control()` → `start_service(project)` → `subprocess.Popen(... preexec_fn=os.setsid ...)` → `save_pid(proc.pid)` → startup verification → PID store → `is_pid_alive` → status reconciliation (`_mark_running`)

Relevant files:
- `yasineco/YasinHub/yasinhub/service_manager.py:140-237` (start_service)
- `yasineco/YasinHub/yasinhub/pid_store.py:42-71` (is_pid_alive with waitpid WNOHANG + kill 0)
- `yasineco/YasinHub/yasinhub/process_checker.py:24-40` (pgrep -f)
- `yasineco/YasinHub/yasinhub/report.py:81-162` (build_report reconciliation)
- `yasineco/YasinHub/yasinhub/api/server.py:69-86` (HTTP control route returns result of start_service as `success`)
- `yasineco/YasinRelay/yasinrelay/cli.py:54-110` (Relay CLI exits with code 1 if channels empty before scheduler)
- `yasineco/YasinRelay/.venv/bin/yasinrelay-termux` (bash wrapper with LD_PRELOAD + exec)

## Root Cause

1. **Relay timing with empty config:** `yasinrelay/cli.py:91-94` returns `1` with `logger.error("هیچ کانال منبعی...")` BEFORE scheduling. Measured on this device:

```
time yasinrelay-termux run --schedule --non-interactive
# → 1.059s real, exit 1
```

Environment verified: `yasineco/YasinRelay/.env` has `SOURCE_CHANNELS=` (empty). Commit 5965c64 fixed termux launcher to use `--non-interactive` (avoiding interactive prompt) but left timing window short.

2. **Hub verification window too short:** `service_manager.py:211-213`
```python
save_pid(project.name, proc.pid)
time.sleep(0.3)
if proc.poll() is not None:
    ... return False
```
At 0.3s, Relay is still in Python startup (import overhead, ~1s total). `proc.poll()` is `None`, so Hub returns `True`, marks `_mark_running`, and closes log. 0.7s later Relay exits with code 1, leaving:
- PID file still present (`~/.yasinhub/pids/yasinrelay.pid`)
- Process dead / zombie until reaped via `os.waitpid` in `is_pid_alive`
- Dashboard `build_report` eventually reconciles via `is_pid_alive` → `PID Z`/dead → shows STOPPED, but API already returned false success.

3. **No zombie / post-start liveness verification:** `start_service` only checks `proc.poll()` once. It never calls `is_pid_alive(pid)` or `/proc/<pid>/state` check, nor does it loop. The existing `is_pid_alive` (pid_store:48-53) correctly handles zombie via `waitpid(WNOHANG)` but is not used during startup. `process_checker` uses `pgrep -f` which self-matches test commands and is not used for startup verification.

4. **HTTP layer propagates false success:** `api/server.py:82-86` blindly returns `{"success": result}` where result is the boolean from `start_service`. No additional authoritative check.

## Observed Behavior (reproduced)
- `SOURCE_CHANNELS` empty → Relay exits 1 after ~1.06s
- `start_service` with 0.3s window → returns `True` (false success)
- PID file exists, `is_pid_alive(pid)` → after waitpid returns False (dead)
- `build_report` will later remove PID and show IDLE/FAILED, but initial START response was wrong.

## Expected Behavior
A START operation MUST NOT report success when:
- child immediately exits (exit code !=0)
- child becomes zombie
- expected PID no longer exists or `is_pid_alive` is False
- startup verification fails within window

Successful START must mean:
- valid PID exists
- `is_pid_alive(pid)` is True (including waitpid zombie reap)
- process survives startup verification window (≥ actual Relay startup time + margin)
- status correctly reconciled to RUNNING only after verification

## Proposed Fix
Minimal correct production fix in `service_manager.py:start_service`:

- Replace single `time.sleep(0.3)` + `poll` with looped verification window, e.g. 2.0s total (configurable), polling every 100-200ms:
  ```
  deadline = time.time() + 2.0
  while time.time() < deadline:
      if proc.poll() is not None:  # exited
          remove_pid; write_status failed; return False
      if not is_pid_alive(proc.pid):  # zombie or dead without poll yet
          remove_pid; return False
      time.sleep(0.15)
  # final verification
  if proc.poll() is not None or not is_pid_alive(proc.pid):
      return False
  ```
- Optionally verify `/proc/<pid>/status` not `Z` state via direct read as defense-in-depth (pid_store already handles via waitpid).
- Keep `_mark_running` only after window succeeds.
- Add regression test specifically covering empty-config zombie scenario (start with command that sleeps 1s then exits 1).

Do NOT require external source channels to validate startup; empty config case must fail truthfully.

## Regression Test Plan
- Test `test_zombie_false_success` that starts dummy service with `python3 -c "import time,sys; time.sleep(1); sys.exit(1)"` and asserts `start_service` returns `False`, PID removed, no false RUNNING status, `is_pid_alive` False.
- Also verify real `yasinrelay` with empty SOURCE_CHANNELS returns failure (if env allows).
- Rerun Hub lifecycle suite: `test_real_process_lifecycle_contract`, `test_pwa_api_control_endpoint_execution` after fix.

## Next
Checkpoint 18 — implement fix, run regression, commit evidence.
