# Checkpoint 04 — REAL START LIFECYCLE

## Status
PARTIAL

## Started
2026-09-05T02:35:00+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:41:00+03:30 (Asia/Tehran)

## Environment
- Hub PID: 14793 healthy at 127.0.0.1:8000
- YasinRelay: main @6bbe6d4, start_command .venv/bin/yasinrelay-termux run --schedule --non-interactive, .env empty (operator config missing)
- Dummy service: test_dummy_service with python3 -c "import time; time.sleep(30)", pattern time.sleep
- PIDs dir: cleaned empty before Hub start, then yasinrelay.pid 20806 zombie, test_dummy_service.pid 20823 alive

## Actions
- Attempted START yasinrelay via Hub Control Plane: POST /api/control/yasinrelay/start (curl -X POST http://127.0.0.1:8000/api/control/yasinrelay/start)
- Observed Hub API response and yasinrelay PID file, checked /proc/<PID>/cmdline, ps, dashboard
- Created dummy service test_dummy_service via yasinhub.service_manager.start_service directly (proving Hub PID mechanics with real process)
- Verified real PID existence, liveness via is_pid_alive and pgrep, checked cmdline, performed 3s stability window, checked process_checker and dashboard authoritative state
- Recorded HTTP status, timestamps, PID values

## Evidence
- **YasinRelay via Hub (real Relay path):**
  - Request: `curl -s -X POST http://127.0.0.1:8000/api/control/yasinrelay/start -H "Content-Type: application/json" -d '{}'`
  - HTTP Status: 200
  - Response: `{"action":"start","service":"yasinrelay","success":true}` (Hub claims success)
  - Real child PID saved: 20806 (from /data/data/com.termux/files/home/.yasinhub/pids/yasinrelay.pid)
  - `ps -o pid,ppid,cmd` shows: `20806 14793 [python] <defunct>` — zombie, State Z, PPid 14793 (Hub), Tgid 20806, Threads 1
  - `/proc/20806/cmdline` readable but shows empty/truncated due to zombie; `cat /proc/20806/status` shows State: Z (zombie), Name: python
  - `is_pid_alive(20806)` via pid_store returns True (kill0 succeeds, waitpid ChildProcessError because caller is not parent) — false alive detection for zombie
  - `ps aux | grep yasinrelay` does NOT show alive yasinrelay.cli process (no real running yasinrelay, only zombie)
  - `check_process("yasinrelay.cli")` returns True with pids=['20895'] which is actually the checker bash command itself containing the string "yasinrelay.cli" (false positive due to pgrep matching checker)
  - YasinRelay log tail `/data/data/com.termux/files/home/.yasinhub/logs/yasinrelay.log` last line: `2026-09-05 02:35:07,102 - __main__ - ERROR - هیچ کانال منبعی تنظیم نشده است (SOURCE_CHANNELS یا --channel)` — proves Relay exited due to empty operator config after Hub's 0.3s poll window, became zombie not reaped
  - Dashboard GET /api/dashboard after start: yasinrelay entry status RUNNING, message "observed running", last_run updated — Hub reports RUNNING despite zombie (stale)
  - Log verification: YasinRelay .env is empty (EITAA_TOKEN=, SOURCE_CHANNELS=, confirmed via od -c), so start *should* fail closed; Hub's 0.3s window too short to catch Relay's 0.5-1s startup failure, hence false success
  - **Conclusion:** Hub accepts START, returns success true, but real Relay does not remain alive; PID is zombie not a valid Relay process. This is a lifecycle defect + operator config blocker.

- **Dummy service via Hub service_manager (proves Hub PID mechanics):**
  - Command: `ProjectEntry(name="test_dummy_service", start_command='python3 -c "import time; time.sleep(30)"', process_pattern='time.sleep')` via `start_service(test_project, logs_dir=~/.yasinhub/logs)`
  - Returned: started True
  - Real PID: 20823 (from pids/test_dummy_service.pid, 5 bytes)
  - `ps -p 20823 -o pid,cmd` = `20823 python3 -c import time; time.sleep(30)`
  - `/proc/20823/cmdline` = `python3 -c import time; time.sleep(30)` (verified via `tr '\0' ' '`)
  - `is_pid_alive(20823)` = True
  - `pgrep -f "time.sleep"` = 20823, 20895 (20823 is dummy, 20895 is checker)
  - `check_process("time.sleep")` = true with pids [20823, 20895] — correctly detects dummy when using simple pattern (full pattern with semicolon fails due to pgrep regex, documented in 01)
  - Stability window: sleep 3s, after 3s `is_pid_alive(20823)` still True, `check_process("time.sleep")` still true, process remains alive
  - Timestamp: start at 2026-09-05T02:35:06+03:30, stability verified at 2026-09-05T02:35:09+03:30
  - Pids dir after start: contains test_dummy_service.pid 20823 and yasinrelay.pid 20806 (zombie)
  - No second Control Plane, Hub is sole authority via pid_store save_pid

## Verification
- Hub accepts START for yasinrelay: YES (HTTP 200, success true) — but real Relay process does NOT remain alive due to missing operator config and Hub poll-window bug, resulting in zombie false RUNNING. This is FAIL for Relay-specific lifecycle but expected BLOCKED due to operator config + defect.
- Dummy service proves Hub's real PID mechanics work: real child PID 20823 exists, belongs to expected python sleep process, remains alive during stability window, PID consistent, API/dashboard would reflect if dummy were in registry (proves Hub can spawn and track real PIDs correctly)
- PID identity verified via /proc/<PID>/cmdline for dummy (yasinrelay zombie prevents identity check for Relay)
- No fabrication: all PIDs (20806 zombie, 20823 alive) are real OS PIDs, logs and ps outputs are real

## Blockers
- YasinRelay real start blocked: operator configuration missing (EITAA_TOKEN=, SOURCE_CHANNELS= empty in .env) plus Hub's 0.3s poll window too short to detect Relay's fast exit (results in zombie and false success). This is both BLOCKED (operator) and defect (zombie not reaped, false RUNNING).
- pgrep pattern with semicolon fails for dummy full pattern (needs simple substring "time.sleep") — not blocking but noted
- YasinRelay log shows ModuleNotFoundError history from prior system-python runs, but current run with .venv correctly finds requests and fails only due to empty channels (truthful)

## Next Step
05-stop-lifecycle.md — STOP the running dummy (and attempt to STOP zombie yasinrelay) via Hub and verify termination, PID cleanup, API state.

## Resume Instructions
- Hub is still PID 14793, dummy PID 20823 is alive, yasinrelay zombie 20806 exists. To resume: verify `curl -s http://127.0.0.1:8000/api/health` (200) and `ps -p 20823 -o pid,cmd` (alive) and `ps -p 20806 -o pid,cmd` (zombie). Next: STOP both via `python -c "from yasinhub.service_manager import stop_service; from yasinhub.registry import default_registry; [stop_service(p) for p in default_registry() if p.name=='yasinrelay']"` and dummy `stop_service` or via API POST /api/control/<service>/stop.
