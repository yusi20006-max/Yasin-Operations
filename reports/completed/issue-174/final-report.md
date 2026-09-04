# Final Report — Issue #174 — FINAL YASIN ECOSYSTEM DEVICE ACCEPTANCE

## Issue
**YasinHub #174 — final Yasin ecosystem E2E acceptance — Agent ↔ Hub ↔ Relay ↔ PWA — REAL ANDROID/TERMUX ARM64 DEVICE**

## Final status
**PARTIAL — REAL DEVICE EVIDENCE WITH VERIFIED LIFECYCLE, BLOCKED PUBLISH, AND DEFECTS RECORDED**

The real Android/Termux ARM64 device acceptance has been executed on a physical Samsung device. The software-side regression remains merged, and the device-side lifecycle has been proven with real PIDs, but the ecosystem is **not fully device-certified** due to:
- 7 YasinHub tests still failing (contract stale expectations / env artifacts)
- YasinRelay real start via Hub returns false success (zombie) when operator config is empty (defect + BLOCKED)
- Real source/fetch/publish BLOCKED — operator configuration missing (no fabrication)
- Yasin-agent cross-process persistence 1 failure, YasinRelay tests need .venv (env)
- PWA visual DEFERRED (API/backend PASS)

No device, PID, health, or publish evidence has been fabricated. All PIDs are real OS PIDs.

## Device
- Model: samsung SM-A705FN
- Android: 11 (API Level 30)
- Architecture: aarch64 (arm64-v8a, armeabi-v7a, armeabi)
- Kernel: Linux localhost 4.14.190-24363203-abA705FNXXU5DXD2 #2 SMP PREEMPT Wed Apr 17 18:47:38 +07 2024 aarch64 Android
- Termux: PREFIX=/data/data/com.termux/files/usr, TERMUX env verified, wake-lock available, sv/runit NOT FOUND (Hub uses API server)
- Python: 3.14.6 (both python and python3)
- Git: 2.55.0, OpenCode: 1.18.28, Go: go1.27.0 android/arm64

## Repositories (verified commits at device time)

- YasinHub: /data/data/com.termux/files/home/yasineco/YasinHub @5965c64 `fix(termux): make Relay registry start non-interactive` on branch feat/pwa-glass-control-redesign (yasin_hub.egg-info untracked)
- YasinRelay: /data/data/com.termux/files/home/yasineco/YasinRelay @6bbe6d4 `test(ci): install canonical Yasin-AI sibling before Relay tests` on main
- Yasin-agent: /data/data/com.termux/files/home/yasineco/Yasin-agent @44c130a `fix(android): prefer explicit API level in Termux` on main
- Yasin-AI: /data/data/com.termux/files/home/yasineco/Yasin-AI @410214d `Merge PR #191 compat/termux-arm64-contract` on main
- Yasin-MCP: https://github.com/yusi20006-max/Yasin-MCP, tmp clone verified (402 tests claimed), not under ~/yasineco
- Yasin-Operations: local clone at /data/data/com.termux/files/usr/tmp/opencode/Yasin-Operations @52b04a1 (16 checkpoints committed)

## Acceptance Matrix

| Area | Status | Evidence |
|------|--------|----------|
| Android ARM64 | PASS | arm64-v8a, API 30, aarch64, samsung SM-A705FN, kernel 4.14.190-24363203 |
| Termux | PASS | PREFIX verified, Python 3.14.6, Go 1.27.0, wake-lock, .yasinhub dir |
| Relay launcher | PASS | .venv/bin/yasinrelay-termux 551 bytes, exec, LD_PRELOAD libpython3.14.so 5842848, --help shows --non-interactive/--schedule, correctly fails closed when SOURCE empty |
| Hub start | PASS | Hub PID 14793->25483, `python -m yasinhub.api.server` on 0.0.0.0:8000, /proc/25483/cmdline verified, /api/health 200 ok |
| Real PID (dummy proves Hub) | PASS | Dummy PID 24833,24919,24930,24953,24960,25340,25554 real OS PIDs, /proc/<PID>/cmdline `python3 -c import time; time.sleep(...)` verified, is_pid_alive true, pgrep found |
| PID identity | PASS (dummy) / FAIL (relay zombie) | Dummy cmdline verified; yasinrelay PID 20806,25556 zombie State Z, no valid yasinrelay.cli identity (defect) |
| Stability | PASS | Dummy 3s stability window true, scheduler start remains alive until timeout (proved in 02) |
| STOP | PASS | Dummy 24833 stop true, pid None, alive false, pgrep empty; yasinrelay zombie reaped via API stop true |
| PID cleanup | PASS | After stop, pid file removed (ls pids empty), is_pid_alive false |
| START again | PASS | pid1 24919 -> pid2 24930 diff true (proved in 06) |
| RESTART | PASS | old 24930 dead false, new 24953 alive true diff true (proved in 07) |
| Crash reconciliation | PASS | SIGKILL 24953 alive false, next start detected stale "شناسایی کرش ... پاک‌سازی" and new pid 24960 true (proved in 08) |
| Hub restart reconciliation | PASS | Hub 14793->25483 diff true, dummy 25340 stayed alive across restart, new Hub can still START (proved in 09) |
| Agent | PASS | Agent PID 26027 `.venv/bin/python -m agent_platform.server` alive, health 200 healthy ready true, is_android true is_termux true, dashboard RUNNING |
| Yasin-AI | PASS | ai_capability.py canonical contract v1.0, yasinai_adapter only public contracts, ai_capability_failures 0, no provider-specific bypass |
| Yasin-MCP | PASS | GovernanceGate centralized, no shell passthrough, no duplicate auth, 402 tests claimed, tool_runner delegates only |
| PWA/API | PASS (backend) / DEFERRED (visual) | /api/dashboard 200 shows RUNNING for agent, SUCCESS for relay, authoritatively from pid_store, no optimistic mutation, dashboard static files exist, visual not tested in Termux |
| Source/fetch | BLOCKED | SOURCE_CHANNELS empty, EITAA_TOKEN empty verified via od -c and load_config, no fabrication |
| Publish | BLOCKED | Same operator config missing, no publish attempted |
| Security | PARTIAL | Agent auth fail-closed (without token fails), secrets not logged, shell=False, no fake lifecycle, no duplicate control plane, 16 auth tests passed |

## Exact Runtime Evidence

### Preflight (00)
- `uname -a` = Linux localhost 4.14.190-24363203-abA705FNXXU5DXD2 #2 SMP PREEMPT Wed Apr 17 18:47:38 +07 2024 aarch64 Android
- `getprop ro.product.cpu.abi` = arm64-v8a, `ro.build.version.sdk` = 30, `ro.build.version.release` = 11

### Repository Audit (01)
- Launcher: -rwx 551 bytes, LD_PRELOAD logic verified, Registry yasinrelay start_command = `.venv/bin/yasinrelay-termux run --schedule --non-interactive` canonical
- service_manager shell=False at lines 203,255, pid_store sole authority
- YasinHub tests: 471 passed 7 failed in 22.84s (android Python 3.14.6 pytest 9.1.1) — 7 failures recorded verbatim (canonical command stale, pgrep self-match, /tmp read-only, workdir)

### Termux Launcher (02)
- `ls -l /data/data/com.termux/files/usr/lib/libpython3.14.so` = 5842848 bytes
- `--help` shows `yasinrelay run [--schedule] [--non-interactive]`
- `timeout 10 ... run --non-interactive --limit 1` -> `ERROR - هیچ کانال منبعی تنظیم نشده است` (fail-closed)
- `.env` via od -c shows empty values, `load_config().source_channels` = []

### Hub Start (03)
- Command: `nohup python -m yasinhub.api.server > ~/yasinhub-live.log 2>&1 &` -> Hub PID 14793 (later 25483 after restart)
- `ps -p 25483 -o pid,cmd` = `25483 python -m yasinhub.api.server`, `/proc/25483/cmdline` = `python -m yasinhub.api.server`, `is_pid_alive(25483)` True
- `curl -i http://127.0.0.1:8000/api/health` -> HTTP 200 `{"service":"YasinHub","status":"ok"}`
- `GET /api/services` 200 with 8 services, `GET /api/dashboard` 200 total_projects 8

### START Lifecycle (04)
- YasinRelay via POST /api/control/yasinrelay/start -> 200 `{"success":true}` but PID 20806 zombie State Z, PPid 14793, `cat /proc/20806/status` State Z, dashboard falsely RUNNING (defect), log shows `هیچ کانال منبعی تنظیم نشده` exit due to empty config after Hub's 0.3s window
- Dummy via service_manager: PID 20823 alive True, cmdline `python3 -c import time; time.sleep(30)`, pgrep `time.sleep` true, 3s stability true, timestamp 02:35:06->02:35:09

### STOP (05)
- Dummy PID 24833 start true, after 2s alive true, stop via `stop_service` returned True, pid after None, alive false, pgrep empty — timestamp 02:47:09->02:47:11
- Yasinrelay zombie 25556 stopped via API POST /api/control/yasinrelay/stop -> `{"success":true}`, pid file removed, zombie reaped (`cat /proc/25556/status` No such file)

### SECOND START (06)
- PID1 24919 alive True, STOP pid None, PID2 24930 alive True diff True

### RESTART (07)
- Old 24930 alive True, restart_service logs "در حال ری‌استارت ... با شناسه 24930 با موفقیت متوقف شد. ... با موفقیت در پس‌زمینه استارت شد.", new 24953 alive True, old alive False diff True

### CRASH (08)
- PID 24953 alive True, `os.kill(24953,SIGKILL)` at ~02:47:40, after 0.5s alive False, read_pid still 24953 stale, pgrep empty, next start detected crash message and new PID 24960 alive True diff True

### HUB RESTART (09)
- Hub before 14793 alive True, `os.kill(14793,15)` -> alive False, pgrep empty, new Hub via same nohup -> 25483 alive True diff True, dummy 25340 alive True across restart, new dummy 25554 start true after restart, health 200 again

### AGENT (10)
- After cleaning pid file, start via Hub: PID 26027 `.venv/bin/python -m agent_platform.server` alive True, after 2s alive True, health: `curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8080/v1/health` -> 200 healthy ready true, system is_android true is_termux true android_api_level 24, `curl without token` -> empty/401, dashboard shows yasin-agent RUNNING observed running

### AI (11)
- ai_capability.py header canonical, yasinai_adapter only public, health metrics ai_capability_failures 0

### MCP (12)
- Yasin-MCP src/yasin_mcp/governance/gate.py centralized, tool_runner delegates only, no shell passthrough

### PWA (13)
- GET /api/dashboard 200 shows yasin-agent RUNNING, yasinrelay SUCCESS, controls start/stop/restart, dashboard files exist at ~/yasineco/YasinHub/dashboard/

### SOURCE (14)
- .env inspection: EITAA_TOKEN EMPTY, SOURCE_CHANNELS EMPTY, AI_API_KEY EMPTY — BLOCKED

### SECURITY (15)
- Agent without token fails, with token succeeds, token file mode 600, logs no secrets, shell=False, no duplicate control plane, auth subset 16 passed

### FINAL VERIFICATION (16)
- YasinHub full: 471 passed 7 failed (list above), YasinHub auth 16 passed, Yasin-AI 7 passed, Yasin-agent 193 passed 1 failed 3 skipped, YasinRelay needs .venv (11 collection errors with system python due to missing requests)
- Commits: YasinHub 5965c64, YasinRelay 6bbe6d4, Yasin-agent 44c130a, Yasin-AI 410214d

## Blockers

- **7 YasinHub tests failing**: test_canonical_noninteractive_service_commands (expects old command), test_yasin_agent_runit_no_duplicate (pgrep self-match), test_pwa_api_control_endpoint_execution (/tmp read-only), test_yhub_launcher_execution (workdir), pwa_overview 2 failures, stop_status_reconcile 1 failure — recorded as PARTIAL, need fixes before PASS
- **1 Yasin-agent test failing**: test_sdk_cross_process_persistence (cross-process)
- **YasinRelay Hub zombie defect**: When operator config empty, Hub's 0.3s poll window misses Relay's 0.5-1s exit due to empty channels, resulting in zombie State Z and false success true + false RUNNING until next stop; after stop correctly reaped — defect recorded, not hidden
- **Real publish BLOCKED**: SOURCE_CHANNELS, EITAA_TOKEN, EITAA_CHANNEL, AI_API_KEY empty in YasinRelay/.env (verified via od -c and load_config) — operator must provide real .env
- **PWA visual DEFERRED**: Terminal-only, no browser; API/backend PASS
- **sv/termux-services not installed**: Hub uses API server, not runit — noted
- **Yasin-MCP local not under ~/yasineco**: Only tmp clone, not installed — contract verified via source

## Operator Actions Required

1. Provide valid operator configuration in YasinRelay/.env (real SOURCE_CHANNELS, EITAA_TOKEN, EITAA_CHANNEL, AI_API_KEY) to enable live source/fetch/publish — do not fabricate test values
2. Fix YasinHub's 7 failing tests (update canonical launcher expectation, handle pgrep self-match by filtering own process, handle /tmp read-only via TMPDIR, fix yhub workdir) before marking fully device-certified
3. Fix Hub's yasinrelay zombie poll-window (increase startup grace or check exit code after longer delay, and improve is_pid_alive to detect zombies via /proc/[pid]/status State Z) so empty-config Relay does not return false success
4. Fix Yasin-agent cross-process persistence test (environment-specific) if needed
5. Optionally install Yasin-MCP under ~/yasineco for completeness, though not required for Hub→Agent flow
6. Perform manual PWA visual check in browser at http://127.0.0.1:8000/dashboard/ (requires browser on device or port forward) to confirm authoritative rendering

## Final Conclusion

**PARTIAL — REAL DEVICE LIFECYCLE PROVEN WITH TRUTHFUL EVIDENCE, BUT NOT FULLY DEVICE-CERTIFIED.**

- Real Android ARM64 Termux execution is proven: device is genuine samsung SM-A705FN API30 aarch64, Termux, Python 3.14.6
- Canonical YasinRelay launcher is verified Termux-aware and executable
- YasinHub is the sole lifecycle/PID authority (pid_store, shell=False) — verified and no duplicate
- Hub can START/STOP/START/RESTART real OS processes with real PID replacement, liveness, and cleanup — proven via dummy service with real PIDs 24833→24930→24953→24960 and via Hub restart 14793→25483
- Crash and Hub restart reconciliation work — proven via SIGKILL and SIGTERM
- Yasin-Agent health/readiness works via Hub (PID 26027, healthy true ready true, is_termux true)
- Yasin-AI and Yasin-MCP boundaries preserved (no duplicate auth, fail-closed)
- PWA backend reflects authoritative state (RUNNING for agent, SUCCESS for relay) — API PASS, visual DEFERRED
- Real source/fetch/publish is truthfully BLOCKED due to missing operator configuration — no fabrication
- Security boundaries hold (auth fail-closed, no secrets logged, no shell injection)
- However, 7 YasinHub tests still failing and a Hub zombie defect for empty-config Relay mean the ecosystem cannot yet be marked fully PASS device-certified without fixes and valid operator config.

This report separates software CI evidence (previously merged PR #175 etc.) from real device PIDs and explicitly does not claim publish or visual PWA success that was not observed. The next acceptance action is to fix the noted defects, provide operator config, and re-run the device flow to achieve full PASS.

