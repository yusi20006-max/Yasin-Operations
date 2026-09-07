# YasinHub Registry Repair — execution report

## Basis
- Audit: `reports/active/yasinhub-service-registry-audit/latest.md` (commit `13eb008`), YasinHub HEAD `435a1832…`.
- Scope obeyed: registry/YasinHub wiring only. No fake executables, no second control plane, `shell=False` kept, PID-verification contract untouched, no secrets, `yasin_hub.egg-info/` uncommitted.

## Code changes (YasinHub, branch `fix/registry-wiring-repair`, commit `aec9289`)
1. `yasinhub/registry.py` — yasinfeed: `process_pattern yasinfeed.py → yasinfeed.main`; `start_command → "env YASINFEED_PORT=8101 python3 -m yasinfeed.main"` (canonical `python -m yasinfeed.main` per YasinFeed README; `env VAR=…` prefix survives `shlex`/`shell=False` and resolves the :8000 clash with Hub — proven: default port dies with `Errno 98 Address already in use`, `YASINFEED_PORT=8101` runs clean).
2. `yasinhub/registry.py` — yasinpress: `path: null → ~/yasineco/YasinPress-Rewrite-` (exact spelling); `start_command → "python3 -m yasinpress.cli.main run"` (`cli/` has no `__main__.py`, so `-m yasinpress.cli` cannot work; `run` enters the daemon tick loop).
3. `yasinhub/service_manager.py` — spawn adds `stdin=subprocess.DEVNULL` (only addition; `shell=False` preserved). Guarantees unattended start: press `getpass`/`input()` hit EOF fallbacks instead of blocking. Test-compatible (no exact-Popen assertions in suite).
- Live operational config `~/.yasinhub/config.yaml` synced for feed + press (incl. `Yasinfeed-main → Yasinfeed` drift removal; behavior-neutral via canonicalizer). Stale entries (eitaa/coder/backup) intentionally UNCHANGED: no retired semantics exist in config schema, and `tests/test_config_manager.py:20` pins `eitaa_news_v2` in defaults — removal would break contract + tests. Documented as retirement-pending product decision.
- Environment provisioning (child interpreter is system `python3`): `pip install feedparser httpx jdatetime tzdata` (pure-python; feed 6.0.14, httpx 0.28.1, jdatetime 6.1.0, tzdata 2026.3). Verified: `import yasinfeed.main` OK, `yasinpress.runtime_factory` import OK afterwards.

## Verification (all live, Hub restarted on repaired code)
- Tests: `pytest tests/ -q` → **506 passed, 1 failed** (`test_pwa_ui_verification::test_css_design_tokens_and_dark_mode` — proven pre-existing: fails identically on pristine `435a183` via stash check; CSS-only, unrelated).
- yasinfeed lifecycle: `start → success:true RUNNING pid 6102` (child of Hub, cmdline `python3 -m yasinfeed.main`); alive 6s+; own API `GET 127.0.0.1:8101/api/health → ok` with matching pid; `stop → pid null IDLE`, PID dead (`ProcessLookupError`). **FIXED.**
- Noted race (no code change): first repaired start reported success then died — engine init (~1s) overlapped the 2s grace before the :8000 bind crash. Root cause proven via foreground runs, fixed via port env. No Hub defect filed (grace semantics unchanged).
- yasinpress non-interactive startup: `start → RUNNING pid 6352`; fd 0 = `/dev/null`; passed credential prompts via EOF fallbacks (no `.env` created, no secrets); opened `yasinpress.db`; resident 60s+ in tick loop; flushed log shows real work (`30 news received from isna/mehrnews/ilna/irna`, `Queue Dispatch: 20 jobs, 20 succeeded`); `stop → dead, IDLE`. **FIXED.**
- Non-service/stale: `pgrep` for eitaa/coder/backup → none running; entries untouched. backup NOT daemonized per rules.
- PWA: `GET /dashboard/ → 200`; `GET /api/status → 200`: RUNNING = yasinrelay, yasin-agent, yasin-ai (feed + press IDLE after verified stop; 3 FAILED = eitaa/coder/backup as decided).

## Outcome
- REPAIR: PARTIAL (2/2 wiring fixes live-verified; 3 stale entries deliberately UNCHANGED pending retirement decision — no mechanism exists to retire without breaking config schema/tests).
- YASINFEED: FIXED. YASINPRESS: FIXED. BACKUP_MANAGER: UNCHANGED (one-shot, retire-pending). EITAA_NEWS_V2: UNCHANGED (stale, retire-pending). YASIN_CODER: UNCHANGED (stale, retire-pending).
- PWA: PASS (HTTP 200 dashboard/status; browser Network-panel proof remains NOT VERIFIED per standing scope).
- Working tree: YasinHub branch `fix/registry-wiring-repair` pushed; only the 2 source files committed. `yasin_hub.egg-info/` left untracked.
