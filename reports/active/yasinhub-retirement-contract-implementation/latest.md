# YasinHub Retirement Contract — implementation report

## Basis
- Retirement audit `../yasinhub-retirement-contract-audit/latest.md` (commit `23daa6c`); repair base `aec9289`.
- Naming: codebase had no enabled/disabled convention; `enabled: bool = True` chosen (systemd-style flag idiom; absent = runnable = legacy behavior).

## Changes (YasinHub `fix/registry-wiring-repair`, commit `2b16491`, 5 files, +198/-4)
1. `yasinhub/registry.py` — `ProjectEntry.enabled: bool = True`; the 3 stale entries set `enabled=False`; default-YAML export includes the field.
2. `yasinhub/config_manager.py` — passthrough `enabled=item.get("enabled", True)`; validation rejects non-bool; fallback export includes the field.
3. `yasinhub/service_manager.py` — `start_service` refuses disabled entries (message + False, no spawn/pid/status write). stop/restart needed no change (restart funnels into start; stop without pid returns False spawn-free).
4. `yasinhub/api/server.py` — `/api/services` adds `enabled` and emits `controls: []` for disabled entries (additive field, same shape; dashboard renders buttons from hardcoded actions gated by status, unaffected).
5. `tests/test_retirement_contract.py` — 9 tests covering the 7 required cases (legacy default, YAML load, no-spawn start/stop/restart, deterministic status, active lifecycle, payload compatibility, non-bool rejection).
- Live `~/.yasinhub/config.yaml`: `enabled: false` on backup_manager/eitaa_news_v2/yasin-coder. No implementation built, nothing deleted, backup NOT daemonized, `shell=False` kept, `egg-info` uncommitted, no secrets.

## Verification
- Full suite: **515 passed, 1 failed** (`test_pwa_ui_verification` CSS dark-mode — proven pre-existing on pristine HEAD, unrelated).
- Retired over HTTP: start/stop on all 3 → `success:false`, pid null, **zero spawns** (service logs untouched since pre-retirement; `pgrep` empty). Initial confusion resolved honestly: the `exit code N` text in refusal payloads is the *stored historical* status echoed via snapshot, not a fresh spawn (log mtimes prove it).
- Actives under new contract: feed full lifecycle re-proven (start RUNNING pid 3562 → own API `:8101 ok` → stop → dead); yasinrelay/yasin-agent/yasin-ai untouched RUNNING; dashboard + status HTTP 200.
- No rollback needed: zero compatibility failures (no assertion was weakened; the 2 initial new-test failures were test-authoring bugs — global-Popen-patch leakage and live-config dependence — fixed in the tests, not production).

## Outcome
- SCHEMA: PASS. BACKWARD_COMPATIBILITY: PASS. ACTIVE_SERVICES: PASS.
- BACKUP_MANAGER: RETIRED. EITAA_NEWS_V2: RETIRED. YASIN_CODER: RETIRED.
- REGRESSION: NONE. CODE_CHANGE: YES (Hub commit `2b16491`, pushed).
