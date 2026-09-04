# Checkpoint 18 — Zombie Fix Implementation — Issue #174

**Date:** 2026-09-05 03:08 UTC
**Branch:** fix/final-device-acceptance-174 (yasineco/YasinHub)
**Device:** SM-A705FN Android 11 API30 arm64 Termux

## Fix Summary
Modified `yasinhub/service_manager.py:start_service` to replace single 0.3s poll with authoritative 2.0s startup verification window polling every 0.15s, checking both `proc.poll()` and `is_pid_alive(pid)` (which handles zombie via `waitpid(WNOHANG)+kill0`). Only after surviving window does it mark RUNNING.

**File:** `yasinhub/service_manager.py:211-252`
- Old: `time.sleep(0.3); if proc.poll() is not None: return False`
- New: loop deadline 2.0s, check poll+is_pid_alive every 0.15s, final check, then `_mark_running`.

Also preserves existing stale PID cleanup, log handling, status persistence.

## Evidence — Regression Tests

### Synthetic delayed-exit (Relay surrogate)
Command: `python3 -c "import time,sys; time.sleep(1); sys.exit(1)"`
- Before fix: would return `True` (false success) at 0.3s
- After fix: `result=False`, `pid=None`, log shows `بلافاصله با کد خروج 1` → PASS

Script: `yasineco/YasinHub/test_zombie.py` (removed after test)
Output:
```
--- Test zombie delayed exit (should FAIL) ---
result=False expected False
pid after=None
PASS
--- Test long-running should succeed ---
result=True expected True
pid2=8101 alive=True
PASS
```

### Real YasinRelay with empty SOURCE_CHANNELS
- `yasinrelay start_command = .venv/bin/yasinrelay-termux run --schedule --non-interactive`
- Measured Relay exit: 1.059s, code 1, log `هیچ کانال منبعی تنظیم نشده`
- Before fix: Hub returned `success=true` with zombie PID
- After fix: `result=False`, `pid=None`, log tail confirms error, no false RUNNING → PASS

```
proj start_command=.venv/bin/yasinrelay-termux ...
result=False expected False due to empty SOURCE_CHANNELS
pid=None
log tail: ERROR - هیچ کانال منبعی...
```

## Verification
- Ran lifecycle tests after fix: `test_real_process_lifecycle_contract` still needs isolation but quick check of `test_zombie` PASS.
- Full Hub suite will be re-run in checkpoint 23.

## Commit
Branch `fix/final-device-acceptance-174` contains edit to `service_manager.py`. Report commit pending push isolation (no destructive reset). File verified via `read` after edit.

## Next
Checkpoint 19 — Analyze all 7 Hub test failures individually.
