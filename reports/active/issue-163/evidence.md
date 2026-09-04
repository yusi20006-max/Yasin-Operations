# Issue #163 — Evidence

## E1: START false success (synthetic relay-like service, real processes)

Command: `python3 ~/.yasin-reports/issue-163/repro_start_falsesuccess.py`
Service: `python3 -c "import time,sys; time.sleep(1.2); print('FATAL: no channels'); sys.exit(1)"`
Output:
- `سرویس repro-relay-like با موفقیت در پس‌زمینه استارت شد.`
- `RESULT start_service=True pid_file=11959 alive_after_wait=False`
- `BUG REPRODUCED: success reported but process dead`

## E2: YasinRelay honest-failure code path (code reading)

- `~/yasineco/YasinRelay/yasinrelay/cli.py:93`:
  `logger.error("هیچ کانال منبعی تنظیم نشده است (SOURCE_CHANNELS یا --channel)"); return 1`
  Reached only after imports + config load + logging setup (> 0.3s on device), i.e. after
  the manager's single poll. Hence Hub reports success, then NO RELAY PROCESS.
- `~/yasineco/YasinRelay/scripts/install_termux.sh:78` itself documents the contract:
  `python -m yasinrelay.cli run --channel "@__termux_smoke_test__" --limit 1 || test $? -eq 1`
  (without channels the process exits 1 — honest failure the Hub must surface, not mask).
- No `yasinrelay-termux` wrapper exists in YasinRelay (searched repo + `~/.venv/bin`);
  launcher creation is a separate cross-repo concern.

## E3: Baseline test suite (main, worktree yasinhub-163)

- `python3 -m pytest tests/ -q` → **1 failed, 448 passed** (26s).
- Failure: `tests/test_http_transport.py::test_config_from_env_present`:
  `assert 'ZQqWQvkqkidi...GeBaWK8et8-C8' == 'secret-token'` — real token file overrode the
  injected dict (device has `~/.yasinhub/yasin-agent.token`).

## E4: API propagation

- `yasinhub/api/server.py:82-86` returns `{"service","action","success": <start_service()>}` —
  manager false-success becomes HTTP `{"action":"start","service":...,"success":true}` verbatim.
