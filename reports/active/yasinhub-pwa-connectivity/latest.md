# YasinHub PWA Connectivity Audit — latest

## Test execution time
- UTC: 2026-09-07T04:14:18Z (re-audit on canonical HEAD; first run 2026-09-07T04:09:11Z was on wrong HEAD)
- Device: Android / Termux (same-device curl, no browser automation)
- Operator: opencode (Muse Spark)

## Git / HEAD reconciliation (why first run was on c7ca808)
- Previous runtime HEAD: `c7ca808822d473dbb9101ffcf8ca1b9dc39f8052` on branch `fix/final-device-acceptance-174`.
- Reason: local checkout was on that fix branch (`origin/fix/final-device-acceptance-174`); `c7ca808` exists ONLY on that branch, not in `origin/main` history.
- `git fetch origin` then showed `origin/main = a5a3d22bbd51b9a8b302cf421047957ff8200013`.
- Required commit `435a1832b4e4ab88ae9dfd25c872a1ce5a614a66` EXISTS in `origin/main` history (2nd commit: `a5a3d22 → 435a183 → 1690cbe ...`).
- Diff `435a183..a5a3d22` = cosmetic only (3 files: `dashboard/style.css, dashboard/ui20.css, tests/test_pwa_ui_verification.py`), no API/lifecycle change.
- Action: graceful `stop yasin-agent` via API, killed old Hub (PID 8115), `git checkout 435a1832b4e4ab88ae9dfd25c872a1ce5a614a66` (detached HEAD), started new Hub (PID 13058) from canonical HEAD, re-ran full suite below.

## AUDITED_HEAD
- `435a1832b4e4ab88ae9dfd25c872a1ce5a614a66`
- `git rev-parse HEAD` = `435a1832b4e4ab88ae9dfd25c872a1ce5a614a66`, state `HEAD (no branch)`, `?? yasin_hub.egg-info/` only.
- Subject: `fix(pwa): remove mobile layout blank space and align RTL drawer`

## ORIGIN_MAIN_HEAD
- `a5a3d22bbd51b9a8b302cf421047957ff8200013` (`fix(pwa): stop mobile header overflow from breaking full-page layout`)
- Required `435a183` is the direct parent of `ORIGIN_MAIN_HEAD` and therefore part of `origin/main`. No guessing; verified via `git cat-file -t` (=commit) + `git log origin/main`.

## Health API (on AUDITED_HEAD)
- `GET http://127.0.0.1:8000/api/health` → HTTP 200
- Body: `{"service":"YasinHub","status":"ok"}`
- Header: `Access-Control-Allow-Origin: *`

## Services / Status API (on AUDITED_HEAD)
- `GET /api/services` → HTTP 200, 8 services: `yasinfeed, eitaa_news_v2, yasinrelay, yasin-agent, yasin-ai, yasin-coder, yasinpress, backup_manager`, each `controls:[start,stop,restart]`. Canonical names PRESENT.
- `GET /api/status` → HTTP 200, 8 projects: `yasin-agent RUNNING` (final PID 13312), `yasinrelay IDLE`, `yasin-ai IDLE`, FAILED: `yasinfeed, eitaa_news_v2 (exit 2), yasin-coder, yasinpress (exit 1), backup_manager (exit 2)` — recorded only, not debugged.
- `GET /api/metrics/yasin-agent` → HTTP 200 `status:RUNNING pid:13312`; `GET /api/metrics/yasinrelay` (during smoke) → HTTP 200 `RUNNING pid:13243`.
- `GET /dashboard/` → HTTP 200 `text/html 2669B` PWA shell.
- Token: TOKEN_PRESENT (presence only). Venv: VENV_PRESENT. No secrets recorded.

## Lifecycle smoke (on AUDITED_HEAD)
- `POST /api/control/yasin-agent/start` → HTTP 200 `success:true status:RUNNING pid:13114 process_running:true` (response on this HEAD includes pid/status fields).
- `POST /api/control/yasin-agent/restart` → HTTP 200 `success:true pid:13161`; PID file `13114 → 13161`; new PID ALIVE (`kill(pid,0)` ok, child of Hub 13058, metrics match); old PID 13114 `ProcessLookupError` = DEAD. Real Restart PID change PROVEN.
- `POST /api/control/yasin-agent/stop` → HTTP 200 `success:true status:IDLE pid:null`; previous PID 13161 `ProcessLookupError` = DEAD; `ps` shows no `agent_platform`; metrics `pid:null IDLE`. Stop-dead PROVEN.
- `POST /api/control/yasinrelay/start` → HTTP 200 `success:true pid:13243 RUNNING`; `POST .../yasinrelay/stop` → HTTP 200 `success:true IDLE pid:null`.
- Final: `POST .../yasin-agent/start` → HTTP 200 `pid:13312 RUNNING` (Hub 13058 → agent 13312, left RUNNING).
- No `404 service not found`, no `success:false`, no `409`.

## Agent runtime (on AUDITED_HEAD)
- While agent RUNNING: `GET 127.0.0.1:8080/v1/health` (Bearer from token file, value not recorded) → 200 `healthy ready:true`; `GET /v1/ready` → 200 `ready:true`, `platform:Android arch:aarch64 is_termux:true`.

## TERMUX_EVIDENCE
- Loopback `:8000` all 200 (health/services/status/dashboard/metrics); control POSTs all 200 success:true with pid echo on this HEAD; PID transitions `13114→13161` (restart) and `13161→dead` (stop) proven via pidfile + `os.kill(pid,0)` + `ps`; yasinrelay `13243 RUNNING→IDLE`; agent `:8080` healthy/ready; Hub log `yasinhub-8000-435a183.log` shows matching 200 sequence; CORS `*`.

## BROWSER_EVIDENCE
- NOT VERIFIED. `GET /dashboard/` curl = 200; `Origin`-header curl on `/api/status` = 200 + `Access-Control-Allow-Origin: *`; dashboard JS uses same-origin relative URLs (`dashboard/js/api.js:88 getJSON("/api/status")`, `dashboard/service-controls.js:42 fetch(/api/control/... {credentials:"same-origin"})`). Real device-browser render + Network panel + refresh-PID proof still requires manual open of `http://127.0.0.1:8000/dashboard/`; not faked.

## Real HTTP statuses (re-audit)
- `GET /api/health` 200; `GET /api/services` 200; `GET /api/status` 200; `GET /dashboard/` 200; `GET /api/metrics/*` 200; all 6 control POSTs 200; `:8080/v1/health` + `/v1/ready` 200.

## Real errors
- None on control plane for smoked services. Pre-existing 5x FAILED service statuses recorded above (boundary: service startup failures, not Hub routing failure). Initial `connection refused` belonged to previous run before Hub start, not to this HEAD.

## Defect in YasinHub
- No new real regression proven on `435a183`. No defect commit to record.

## VERDICT
- PARTIAL (all Termux runtime tests PASS on canonical HEAD; withheld from FINAL/PASS only due to missing real-browser evidence).

## CODE_CHANGE
- NO CODE CHANGE
