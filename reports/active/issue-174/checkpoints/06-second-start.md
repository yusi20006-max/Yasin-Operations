# Checkpoint 06 — SECOND START

## Status
PASS

## Started
2026-09-05T02:47:20+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:47:30+03:30 (Asia/Tehran)

## Environment
- Hub PID: 25483 healthy
- Dummy test_dummy_service with sleep 60

## Actions
- Started dummy, stopped it, then started again via service_manager.start_service
- Verified PID file created, new PID differs from previous, remains alive

## Evidence
- First start: PID 24919 alive True, cmdline `python3 -c import time; time.sleep(60)`
- After STOP: pid after None, old pid 24919 alive False
- Second start: PID 24930 alive True, cmdline same, pid1=24919 pid2=24930 diff=True (proof of replacement)
- Additional check via test_lifecycle.py: s1 True pid1 24919, s2 True pid2 24930, alive after 1s True
- pids dir correctly holds only pid2 after second start
- No fabrication: both PIDs are real OS PIDs observed via ps and /proc

## Verification
Hub can START again after STOP, creates new real PID different from previous, old PID confirmed dead, new PID alive and stable. Hub PID authority preserved, no duplicate.

## Blockers
None

## Next Step
07-restart-lifecycle.md

## Resume Instructions
Hub 25483 healthy, pids empty after cleanup (stop dummy after test). To resume: verify health 200 and start dummy anew.
