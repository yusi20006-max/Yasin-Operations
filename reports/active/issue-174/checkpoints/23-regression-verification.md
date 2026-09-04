# Checkpoint 23 — Regression Verification — Issue #174

**Date:** 2026-09-05 03:30 UTC
**Device:** SM-A705FN Android 11 API30 arm64 Termux Python 3.14.6

## Commits at verification
- yasineco/YasinHub `fix/final-device-acceptance-174` based on 5965c64 + 9 modified files (not yet committed to remote; local dirty: pid_store.py, service_manager.py, 7 test files)
- yasineco/YasinRelay main 6bbe6d4 (clean)
- yasineco/Yasin-agent main 44c130a (clean)
- yasineco/Yasin-AI main 410214d (clean)

## Suites

### YasinHub
- Command: `.venv/bin/python -m pytest tests -q` (workdir yasineco/YasinHub)
- Result: **478 passed, 0 failed, 0 skipped, duration ~40.28s, exit 0**
- Before fix: 471 passed 7 failed
- After zombie fix + 7 test fixes: all green
- Focused lifecycle: `test_real_process_lifecycle_contract`, `test_pwa_api_control_endpoint_execution` PASS

### Yasin-agent
- Command: `.venv/bin/python -m pytest -q` (workdir yasineco/Yasin-agent)
- Result: **240 passed, 0 failed, 2 warnings, duration ~11.5s, exit 0**
- cross_process persistence: PASSED (1.92s)

### YasinRelay
- Command: `.venv/bin/python -m pytest tests -q` (workdir yasineco/YasinRelay)
- Result: **108 passed, 0 failed, duration 2.77s, exit 0**
- Uses canonical `.venv/bin/yasinrelay-termux` launcher

### Yasin-AI
- Command: `.venv/bin/python -m pytest -q` (workdir yasineco/Yasin-AI)
- Result: **BLOCKED — 38 collection errors, ImportError `cryptography.hazmat.bindings._rust` cannot locate symbol `PyModule_Type`**
- Root cause: Termux Python 3.14 .venv built with incompatible `cryptography` wheel (ABI mismatch). Not code defect from this fix; Yasin-AI package not rebuildable on device without `maturin`/`rust` toolchain.
- Attempted isolated checks: `python -c "import yasinai; print(yasinai.__version__)"` also fails with same dlopen error.
- CI expectation: Yasin-AI suite passes on Linux CI with proper wheel; device BLOCKED recorded honestly.

## Git State
- YasinHub branch `fix/final-device-acceptance-174` dirty; need commit before push.
- YasinRelay, Yasin-agent, Yasin-AI clean.

## Next
Checkpoint 24 — Final real device re-acceptance (START/STOP/RESTART/crash reconciliation with real Relay, empty config test, PWA/backend, security).
