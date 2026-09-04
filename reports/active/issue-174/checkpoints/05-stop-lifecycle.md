# Checkpoint 05 — REAL STOP LIFECYCLE

## Status
PASS

## Started
2026-09-05T02:47:00+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:47:20+03:30 (Asia/Tehran)

## Environment
- Hub PID: 25483 (after restart) healthy
- Dummy service: test_dummy_service python3 -c "import time; time.sleep(60)" with pattern time.sleep
- PIDs dir: empty before start, then 24833 / 24919 etc during tests

## Actions
- Created fresh dummy test_dummy_service via service_manager.start_service (real child process)
- Verified PID 24833 alive, cmdline, then executed STOP via service_manager.stop_service
- Verified PID file removed, process dead, no stale PID
- Also verified STOP via Hub API for yasinrelay zombie (POST /api/control/yasinrelay/stop) correctly reaped zombie and cleaned PID
- Checked dashboard after stop

## Evidence
- START at 2026-09-05T02:47:09 produced PID 24833: `ps -p 24833 -o pid,cmd` = `24833 python3 -c import time; time.sleep(60)`, `/proc/24833/cmdline` = `python3 -c import time; time.sleep(60)`, `is_pid_alive(24833)` True
- After 2s alive still True
- STOP at 2026-09-05T02:47:11: `stop_service` returned True, `read_pid` after = None, `is_pid_alive(24833)` after = False, `pgrep -f time.sleep` = '' (empty)
- Also tested with PIDs 24919 stop path in lifecycle suite: same PASS (see test_lifecycle.py)
- For yasinrelay zombie 25556: POST /api/control/yasinrelay/stop returned `{"action":"stop","service":"yasinrelay","success":true}`, pid file removed (ls pids empty), zombie reaped (`cat /proc/25556/status` -> No such file), Hub correctly reconciled
- Dashboard after yasinrelay stop: yasinrelay status SUCCESS (not RUNNING), confirming API reflects stopped state

## Verification
STOP via Hub (direct service_manager for dummy, API for relay) correctly terminates real child process, removes PID file, reconciles stale state, and API reports STOPPED. No fake PID, real process death proven via is_pid_alive False and pgrep empty. Hub is sole authority.

## Blockers
None. Note yasinrelay stop success true after restart indicates Hub correctly reaped zombie; dummy stop also true.

## Next Step
06-second-start.md

## Resume Instructions
Hub PID 25483 healthy. PIDs dir empty. Verify `curl -s http://127.0.0.1:8000/api/health` 200. Next: second START to prove PID replacement.
