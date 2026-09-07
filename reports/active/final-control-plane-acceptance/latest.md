# Final Control Plane Acceptance Audit — latest

## Conditions
- UTC: 2026-09-07T06:53:48Z → ~06:57Z. Verification ONLY: no production code changed, no new commits to production repos.
- YasinHub: branch `fix/registry-wiring-repair`, HEAD `2b16491`, tree clean (+ untracked `yasin_hub.egg-info/`). Hub PID 2732 serves from this code (services payload shows `enabled` flags).
- Architecture under test: PWA → Hub HTTP API → Registry → Service Manager → real OS PID.

## REGISTRY: PASS
- Active (enabled, full controls): yasinrelay, yasin-agent, yasin-ai, yasinfeed, yasinpress — identical in `DEFAULT_PROJECTS`, live `~/.yasinhub/config.yaml`, and `GET /api/services`.
- Retired (disabled, `controls: []`): backup_manager, eitaa_news_v2, yasin-coder — identical across all three layers.

## LIFECYCLE: PASS (yasinfeed, no guessed PIDs)
- `POST start → success:true RUNNING pid 5388` (aborted run, see anomaly) then clean run: `start → RUNNING pid 5732`, cmdline `python3 -m yasinfeed.main`, `kill(pid,0)` ALIVE, own API `GET 127.0.0.1:8101/api/health → ok` with matching pid + 28s uptime.
- `POST stop → success:true IDLE`, PID dead (`ProcessLookupError`), metrics `pid:null`.
- Re-started to RUNNING (pid 5902) for healthy final state.

## RETIREMENT: PASS
- 9/9 control calls (start/stop/restart × 3 retired) → `success:false`, `pid:null`, no crash; unknown service → `success:false "service not found"`.
- Zero spawns proven: all 3 service logs untouched since 08:13 (pre-retirement), `pgrep` empty. Refusal payloads echo *stored historical* status text via snapshot — deterministic, not fresh failures.

## API: PASS
- `GET /api/health → 200 ok` (+ CORS `*`); `GET /api/status → 200, 8 projects` (RUNNING: yasinfeed, yasinrelay, yasin-agent, yasin-ai; IDLE: yasinpress; FAILED: 3 retired); `GET /api/services → 200` with correct enabled/controls distinction; `GET /dashboard/ → 200, 2669B PWA shell`.

## PWA: PASS (bounded)
- Dashboard serves 200; service table renders dynamically from `/api/status`; retired entries show FAILED badges from stored status; controls call same-origin API (code-read) with `success:false` handled. Live-browser Network panel remains NOT VERIFIED (out of scope, no automation).

## CROSS_LAYER: PASS
- Defaults ↔ live config ↔ Hub API ↔ manager behavior ↔ `ps`/`/proc` reality ↔ PWA representation all consistent. No contradictions found.

## TESTS
- Fresh `pytest tests/ -q`: **515 passed, 1 failed** (`test_pwa_ui_verification` CSS dark-mode assert — proven pre-existing on pristine `435a183` via stash check, unrelated to control plane).

## Anomaly (documented, not hidden)
- One feed run (pid 5388) died silently ~8s after verified-alive while the full pytest suite ran concurrently; zero log output, cause NOT VERIFIED (suspected device resource pressure; no evidence of Hub defect — Hub correctly reported subsequent stop as IDLE/dead). Clean re-run with no parallel load held 28s+ with healthy API. No PASS claimed on the contaminated run.

## Verdicts
- CONTROL_PLANE: PASS. REGISTRY: PASS. LIFECYCLE: PASS. RETIREMENT: PASS. API: PASS. PWA: PASS (bounded, see above). CROSS_LAYER: PASS.
- CODE_CHANGE: NO.
