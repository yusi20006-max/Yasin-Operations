# Checkpoint 19 — Hub 7 Test Failures Analysis — Issue #174

**Date:** 2026-09-05 03:10 UTC
**Suite:** yasineco/YasinHub (.venv pytest) — 471 passed 7 failed (reproduced 2026-09-05 03:04)
**Command:** `.venv/bin/python -m pytest yasineco/YasinHub/tests -q` from $HOME vs from repo root

## Failure Inventory

### #1 test_dashboard_api_exposes_program_status_data
- **Test:** `tests/test_pwa_overview.py:4` reads `Path("yasinhub/api/server.py")`
- **Output:** `FileNotFoundError: [Errno 2] No such file or directory: 'yasinhub/api/server.py'` when pytest cwd is `/data/data/com.termux/files/home`
- **But:** Passes when `workdir=yasineco/YasinHub` (repo root)
- **Root cause:** Test assumes CWD == repo root. Pytest invocation from parent dir (as in previous acceptance `yasineco/YasinHub/tests` path) breaks relative path. The actual server file exists at `yasineco/YasinHub/yasinhub/api/server.py`.
- **Classification:** STALE TEST HARNESS / workdir issue — not implementation defect. File content assertions still valid.
- **Fix layer:** Update test to resolve path relative to repo root via `Path(__file__).resolve().parents[1]` rather than cwd.

### #2 test_pwa_overview_renders_program_names_and_active_state
- Same file `test_pwa_overview.py:12` reads `Path("dashboard/js/views.js")`
- Same error class as #1. Passes from repo root, fails from $HOME.
- **Classification:** Same — test harness workdir.

### #3 test_calculate_health_dead_process_not_success
- **Test:** `tests/test_stop_status_reconcile.py:16` asserts `calculate_health_state(None, "2026-09-03T10:00:00+00:00", True) == "SUCCESS"`
- **Output:** `AssertionError: 'STALE' == 'SUCCESS'` on 2026-09-05 because `2026-09-03` is >24h old (age 48h → STALE per `report.py:71`)
- **Root cause:** Test uses fixed old timestamp that becomes stale after 24h window (`report.py:70-73` checks `age <=86400`). Not time-relative.
- **Classification:** STALE EXPECTATION — test not mocked to freeze time. Implementation is correct (STALE is intended).
- **Fix layer:** Update test to use recent timestamp (`datetime.now(timezone.utc).isoformat()`) or mock datetime.

### #4 test_yasin_agent_runit_no_duplicate
- **Output:** `assert 4242 == 99999` with stdout `سرویس yasin-agent از قبل با شناسه 4242 در حال اجراست.`
- **Root cause:** `service_manager.start_service` first checks `read_pid("yasin-agent")` which returns stale global PID file `~/.yasinhub/pids/yasin-agent.pid` (value 4242 from prior runs). Test mocks `check_process` to return `running=True pids=["99999"]` but does NOT mock `read_pid`/`is_pid_alive`. The PID file pollution causes early return via saved_pid branch, never reaching pattern check. Also global pid dir not isolated per-test.
- **Classification:** TEST HARNESS DEFECT (global state leakage + incomplete mocking) + environment pollution. No implementation defect; runit dedup logic via `check_process` is correct when PID isolation proper.
- **Fix layer:** Make test mock `read_pid`/`is_pid_alive` or ensure clean PID file before test; also clean `~/.yasinhub/pids` remnants. Alternatively make `start_service` prefer `check_process` ownership — but current order (PID file first) is intentional for crash detection.

### #5 test_canonical_noninteractive_service_commands
- **Output:** `assert '.venv/bin/yasinrelay-termux run --schedule --non-interactive' == 'python3 -m yasinrelay.cli run'`
- **Root cause:** Test expects old launcher `python3 -m yasinrelay.cli run` but canonical since commit 5965c64 is `.venv/bin/yasinrelay-termux run --schedule --non-interactive` (preserves LD_PRELOAD for Yasin-AI, non-interactive for Termux). Registry `yasinhub/registry.py:62` defines new canonical. Test expectation stale.
- **Classification:** STALE EXPECTATION — implementation correct, test outdated.
- **Fix layer:** Update assertion to canonical value.

### #6 test_pwa_api_control_endpoint_execution
- **Output:** `http.client.RemoteDisconnected` + server stderr `OSError: [Errno 30] Read-only file system: '/tmp'` when `l_dir.mkdir(parents=True)` tries `/tmp/global_logs`.
- **Root cause chain:**
  1. Previous test `test_config_manager.py:test_global_singleton_apis` sets `config_manager._manager.config_path` to `/tmp/global_config.yaml` and `reload_config()` loads `logs_dir=/tmp/global_logs` into global singleton `_manager._config`. After test, `monkeypatch` restores `config_path` but NOT `_config`, so global remains polluted with `/tmp/global_logs`.
  2. On Termux, `/tmp` does not exist (only `$PREFIX/tmp` exists); mkdir fails with Read-only.
  3. HTTP handler exception closes connection without response → `RemoteDisconnected`.
- **Classification:** TEST HARNESS DEFECT (global singleton pollution) + TERMUX ENVIRONMENT LIMITATION (`/tmp` absent/read-only). Implementation not defective for normal `~/.yasinhub/logs` case, but should handle mkdir error gracefully? Already `service_manager` catches log file open error but not `mkdir`? Actually it does `l_dir.mkdir` without try? The server's `handle_control` calls `start_service` which does `mkdir` and exception bubbles to HTTP handler causing broken pipe. Should be caught.
- **Fix layers:**
  - Fix singleton pollution: cleanup/restore `_config` after `test_global_singleton_apis` or avoid mutating global.
  - Fix Termux `/tmp` usage: tests should use `$PREFIX/tmp` or `tmp_path` facility, not hardcoded `/tmp`.
  - Harden `service_manager.start_service` mkdir to fall back or report failure instead of unhandled exception (return False).

### #7 test_yhub_launcher_execution
- **Output:** `FileNotFoundError: [Errno 2] No such file or directory: './yhub'` when cwd is `$HOME` or `yasineco` parent.
- **Root cause:** Test does `os.stat("./yhub")` assuming pytest cwd == repo root containing `./yhub` launcher. When invoked from parent dir, fails. Also `+x` bit preservation varies on Termux mounts.
- **Classification:** TEST HARNESS / workdir — implementation launcher exists (`yasineco/YasinHub/yhub` and `~/YasinHub/yhub` present, mode +x).
- **Fix layer:** Resolve launcher path relative to `__file__` or repo root.

## Summary Classification

- REAL CODE DEFECT: None among these 7 is a direct production logic defect except the uncovered mkdir exception leakage (minor) — main zombie defect already fixed in checkpoint 18.
- STALE EXPECTATION: #3, #5
- TERMUX ENVIRONMENT LIMITATION: #6 (`/tmp` vs `$PREFIX/tmp`)
- TEST HARNESS DEFECT / WORKDIR: #1, #2, #4, #6 (singleton), #7

## Next
Checkpoint 20 — apply minimal fixes to correct layer without weakening assertions.
