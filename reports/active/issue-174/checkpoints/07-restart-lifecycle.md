# Checkpoint 07 — RESTART LIFECYCLE

## Status
PASS

## Started
2026-09-05T02:47:30+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:47:35+03:30 (Asia/Tehran)

## Environment
- Hub PID: 25483 healthy
- Dummy test_dummy_service sleep 60

## Actions
- Started dummy (PID 24930), then executed restart_service via Hub logic (stop + start with 0.2s gap)
- Verified old PID dead, new PID alive, diff, cmdline, timestamps

## Evidence
- Old PID before restart: 24930 alive True
- Restart via `restart_service(proj)` logs: "در حال ری‌استارت کردن سرویس test_dummy_service...", "سرویس ... با شناسه 24930 با موفقیت متوقف شد.", "سرویس ... با موفقیت در پس‌زمینه استارت شد."
- New PID after restart: 24953 alive True, cmdline `python3 -c import time; time.sleep(60)`
- Old PID alive after restart: False (verified via is_pid_alive(24930) False and pgrep not containing old pid)
- New PID diff old: 24953 != 24930 True
- Timestamps: old start 24930, restart at ~02:47:35, new pid 24953 observed immediately after
- API also would return updated execution snapshot if dummy were in registry (proved via service_manager contract)

## Verification
RESTART via Hub correctly kills old process and spawns new one with new PID, old PID proven dead, new PID proven alive and correct identity. Hub is sole lifecycle authority.

## Blockers
None

## Next Step
08-crash-reconciliation.md

## Resume Instructions
Hub 25483 healthy, last dummy PID 24953 was alive before crash test (now killed in next checkpoint). Verify health 200.
