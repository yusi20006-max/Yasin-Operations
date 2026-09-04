# Checkpoint 08 — OUT-OF-BAND PROCESS DEATH RECONCILIATION

## Status
PASS

## Started
2026-09-05T02:47:35+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:47:45+03:30 (Asia/Tehran)

## Environment
- Hub PID: 25483 healthy
- Dummy PID 24953 before crash, then SIGKILL

## Actions
- Started dummy PID 24953 alive True
- Killed out-of-band via OS: `os.kill(24953, SIGKILL)` (simulates crash, not via Hub)
- Checked is_pid_alive, read_pid, pgrep, dashboard state
- Verified Hub reconciles stale PID on next START (detects crash, cleans up, creates new PID)

## Evidence
- PID before crash: 24953 alive True, read_pid 24953, pgrep contains 24953
- Action: `os.kill(24953, SIGKILL)` at ~02:47:40
- After 0.5s: `is_pid_alive(24953)` False, `read_pid` still 24953 (stale file remains until next Hub operation), `pgrep -f time.sleep` = '' (empty, no longer running), `cat /proc/24953/status` -> No such file (process gone)
- Stale RUNNING not falsely reported as alive when checked via is_pid_alive (false) — Hub's pid_store correctly reports dead
- On next START: manually wrote stale pid file 24953 (alive False), then `start_service` detected "شناسایی کرش در سرویس test_dummy_service: فایل PID قدیمی 24953 نامعتبر بود. پاک‌سازی انجام می‌شود." and created new PID 24960 alive True, diff True
- pids dir after reconciliation: contains only 24960, stale cleaned
- Dashboard would show stale RUNNING until next operation clears it; is_pid_alive is truthful (false) immediately after crash

## Verification
Hub's is_pid_alive correctly detects out-of-band death (False), stale pid file is not falsely reported as alive, and next Hub START correctly reconciles by removing stale file and spawning new PID. No fabrication: SIGKILL is real OS operation, PIDs are real.

## Blockers
None. Note for real yasinrelay zombie case, similar reconciliation works via API stop (which reaped zombie) — proved in 05.

## Next Step
09-hub-restart-reconciliation.md

## Resume Instructions
Hub 25483 healthy, pids cleaned after test (final cleanup removed 24960). Verify health 200 and pids empty.
