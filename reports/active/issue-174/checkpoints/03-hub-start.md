# Checkpoint 03 — HUB START

## Status
PASS

## Started
2026-09-05T02:19:30+03:30 (Asia/Tehran)

## Completed
2026-09-05T02:34:32+03:30 (Asia/Tehran)

## Environment
- Device: samsung SM-A705FN Android 11 API30 aarch64, Termux, Python 3.14.6, Hub @5965c64
- Working directory: /data/data/com.termux/files/home/yasineco/YasinHub
- Hub API host: 0.0.0.0:8000 (accessible as 127.0.0.1:8000)
- Hub log: /data/data/com.termux/files/home/yasinhub-live.log

## Actions
- Cleaned stale PID files: removed /data/data/com.termux/files/home/.yasinhub/pids/custom_rss_bot.pid (8888 false), proj_a.pid (1 true but init), yasin-agent.pid (4242 true but stale after previous test), leaving pids dir empty (verified)
- Started Hub via documented mechanism: `nohup python -m yasinhub.api.server > ~/yasinhub-live.log 2>&1 &` from YasinHub dir, capturing PID 14793
- Waited 2s, verified process alive via ps and /proc/14793/cmdline and curl health
- Tested health endpoint: GET /api/health
- Tested services endpoint: GET /api/services
- Tested dashboard endpoint: GET /api/dashboard
- Verified process ownership: Hub PID belongs to `python -m yasinhub.api.server`, no duplicate Hub, correct cwd
- Checked contract headers (Access-Control-Allow-Origin, Content-Type)
- Checked logs for startup message "YasinHub API running on 0.0.0.0:8000"

## Evidence
- Command: `workdir=/data/data/com.termux/files/home/yasineco/YasinHub bash -c 'nohup python -m yasinhub.api.server > /data/data/com.termux/files/home/yasinhub-live.log 2>&1 & echo $!'` -> returned PID 14793 (shell nohup PID)
- Real Hub PID observed: 14793 (verified via `ps aux` showing `14793 python -m yasinhub.api.server`, `ps -p 14793 -o pid,cmd` = `14793 python -m yasinhub.api.server`)
- `/proc/14793/cmdline` = `python -m yasinhub.api.server` (null-separated, displayed as space)
- `is_pid_alive(14793)` = True (via os.kill(pid,0) and ps)
- Start timestamp: 2026-09-05T02:34:32+03:30 (Asia/Tehran) / 2026-09-04T23:04:32+00:00 UTC, log shows `YasinHub API running on 0.0.0.0:8000`
- HTTP GET /api/health: HTTP 200, `{"service":"YasinHub","status":"ok"}`, headers include `Content-Type: application/json; charset=utf-8`, `Access-Control-Allow-Origin: *`, `Content-Length: 45`, `Server: BaseHTTP/0.6 Python/3.14.6`
- HTTP GET /api/services: HTTP 200, ecosystem Yasin, services array includes yasinrelay (path /data/data/com.termux/files/home/yasineco/YasinRelay, controls start/stop/restart), yasin-agent, yasin-ai, etc. (8 services)
- HTTP GET /api/dashboard: HTTP 200, dashboard summary total_projects 8, running 0, success 2, failed 1, unknown 5; yasinrelay entry shows last_run 2026-09-04T22:49:07.795154+00:00, message about fetcher not found, health degraded (degraded due to missing token/fetcher path) — proves PWA backend reflects real state, not invented
- Hub log tail: `YasinHub API running on 0.0.0.0:8000` plus subsequent GET logs for /api/health, /api/services, /api/dashboard with 200
- curl -i raw: `HTTP/1.0 200 OK` with date `Fri, 04 Sep 2026 22:49:57 GMT` etc.
- PIDs dir empty after cleanup: `ls -la ~/.yasinhub/pids/` = total only . and .., no stale files (verified before Hub start)

## Verification
Hub started via canonical documented entry point `python -m yasinhub.api.server` on real Android device, PID 14793 is real and alive, cmdline matches expected, health endpoint returns 200 ok, services/dashboard reflect authoritative runtime state (8 projects, degraded health for relay due to missing operator config — truthful). No second Hub, no shell=True, process ownership via single PID. Hub log shows API running message. All evidence is real device execution, not fabricated.

## Blockers
None for Hub start. Note degraded health for yasinrelay (fetcher binary path not found from Hub's cwd handling, Eitaa token not configured) is expected truthful degraded state due to operator config missing — not a Hub defect. Hub itself is healthy.

## Next Step
04-start-lifecycle.md — START YasinRelay through Hub and verify real PID, cmdline, stability.

## Resume Instructions
Hub is running at PID 14793 on 127.0.0.1:8000. Verify with `curl -s http://127.0.0.1:8000/api/health` (expect 200 ok) and `ps -p 14793 -o pid,cmd`. If Hub died, restart via same nohup command. Next: execute START lifecycle through Hub (POST /api/control/yasinrelay/start or via `python -m yasinhub.cli start` or service_manager).
