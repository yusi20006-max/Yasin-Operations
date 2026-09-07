# YasinHub PWA Connectivity Audit — latest

## Test execution time
- UTC: 2026-09-07T04:09:11Z
- Local: 2026-09-07 07:39:11 +0330
- Device: Android / Termux (same-device curl, no browser automation)
- Operator: opencode (Muse Spark)

## YasinHub repo / commit
- Path: `~/yasineco/YasinHub`
- HEAD: `c7ca808822d473dbb9101ffcf8ca1b9dc39f8052`
- Expected HEAD per task: `435a1832b4e4ab88ae9dfd25c872a1ce5a614a66` → MISMATCH (NOT on expected commit)
- Branch: `fix/final-device-acceptance-174` (not `main`)
- Status: `## fix/final-device-acceptance-174...origin/fix/final-device-acceptance-174` + `?? yasin_hub.egg-info/`
- Token: TOKEN_PRESENT (presence only, value not recorded)
- Venv: VENV_PRESENT (`.venv/bin/python`)

## Health API
- `GET http://127.0.0.1:8000/api/health` → HTTP 200
- Body: `{"service":"YasinHub","status":"ok"}`
- Header: `Access-Control-Allow-Origin: *`
- Note: before Hub start, same URL returned `curl (7) connection refused` (Hub was not running). After `nohup .venv/bin/python -m yasinhub.api.server` (PID 8115), health = 200.

## Services / Status API
- `GET /api/services` → HTTP 200, `ecosystem:Yasin`, 8 services:
  `yasinfeed, eitaa_news_v2, yasinrelay, yasin-agent, yasin-ai, yasin-coder, yasinpress, backup_manager`
  each with `controls:[start,stop,restart]`. Canonical names (`yasinrelay, yasin-agent, yasin-ai, yasinfeed`) PRESENT.
- `GET /api/status` → HTTP 200, 8 projects:
  - `yasin-agent RUNNING` (after smoke start; final PID 10787)
  - `yasinrelay IDLE`, `yasin-ai IDLE`
  - `FAILED`: `yasinfeed, eitaa_news_v2, yasin-coder, yasinpress, backup_manager` (messages: exit code 2 / exit code 1 — pre-existing runtime failures, see errors below)
- `GET /api/metrics/yasin-agent` → HTTP 200, `status:RUNNING, pid:10787`
- `GET /api/metrics/yasinrelay` (during smoke) → HTTP 200, `status:RUNNING, pid:10837`
- `GET /dashboard/` → HTTP 200, `text/html 2669B`, Persian PWA shell (`YasinHub` title).

## Lifecycle smoke
- `POST /api/control/yasin-agent/start` body `{"source":"opencode","action":"status"}` → HTTP 200 `{"service":"yasin-agent","action":"start","success":true}`; CLI `status`: `IDLE/stopped` → `RUNNING/observed running`.
- `POST /api/control/yasin-agent/restart` → HTTP 200 `{"action":"restart","service":"yasin-agent","success":true}`.
- `POST /api/control/yasin-agent/stop` → HTTP 200 `{"action":"stop","success":true}` (then started again for final state).
- `POST /api/control/yasinrelay/start` → HTTP 200 `success:true`; `POST .../yasinrelay/stop` → HTTP 200 `success:true` (restored IDLE).
- CLI `python -m yasinhub.cli status` agreed with API at every step.
- No `404 service not found`, no `success:false`, no `409` on the smoked services.

## PID evidence
- Hub: `.venv/bin/python -m yasinhub.api.server`, PID 8115.
- yasin-agent start → PID 10515 (`agent_platform.server` child of Hub, `~/.yasinhub/pids/yasin-agent.pid` = 10515, `/api/metrics` pid matched, `kill(pid,0)=ALIVE`).
- yasin-agent restart → PID 10589 (`10515 → 10589` = new process proven; metrics + `ps` confirmed, old PID gone).
- Final yasin-agent PID after stop/start cycle: 10787 (`RUNNING`, alive, child of 8115).
- yasinrelay start → PID 10837 (`RUNNING`), then stopped (IDLE restored).
- PID store dir: `~/.yasinhub/pids/` (only `*.pid` numbers recorded; token never read into report).

## Browser / PWA reachability evidence
- curl `GET /dashboard/` → 200 (see above).
- curl `GET /api/status` with `Origin: http://127.0.0.1:8000` → 200 + `Access-Control-Allow-Origin: *` → no CORS block expected for same-origin browser at `http://127.0.0.1:8000/dashboard/`.
- Dashboard code uses same-origin relative URLs (no hard-coded cross-origin):
  - `dashboard/js/api.js:88 getJSON("/api/status")`
  - `dashboard/service-controls.js:42 fetch(`/api/control/${svc}/${action}`, {credentials:"same-origin"})`
- Real Android browser render + Network panel (overview table with service names+PIDs, `GET /api/status`, `POST /api/control/<svc>/<action>`, Start/Stop/Restart PID refresh): NOT VERIFIED — OpenCode session has no browser automation; not faked.
- Manual step still required: open `http://127.0.0.1:8000/dashboard/` (or Termux LAN IP if different network namespace) in device browser and confirm table + PID change after refresh.

## Real HTTP statuses observed
- `GET /api/health` → 200
- `GET /api/services` → 200
- `GET /api/status` → 200
- `GET /api/metrics/yasin-agent` → 200
- `GET /api/metrics/yasinrelay` → 200
- `POST /api/control/yasin-agent/start` → 200
- `POST /api/control/yasin-agent/restart` → 200
- `POST /api/control/yasin-agent/stop` → 200
- `POST /api/control/yasinrelay/start` → 200
- `POST /api/control/yasinrelay/stop` → 200
- `GET /dashboard/` → 200
- `GET 127.0.0.1:8080/v1/health` (agent, Bearer auth) → 200 `healthy, ready:true`
- `GET 127.0.0.1:8080/v1/ready` → 200 `ready:true`

## Real errors (if any)
1. Initial `curl: (7) connection refused` on `:8000` — cause: Hub not running. Resolved by starting Hub. Not a code defect.
2. `GET /api/status` shows 5x FAILED (pre-existing, outside connectivity scope but recorded):
   - `yasinfeed: exit code 2`, `eitaa_news_v2: exit code 2`, `yasin-coder: exit code 1`, `yasinpress: exit code 1`, `backup_manager: exit code 2`.
   - Boundary: service runtime/startup failures, not Hub API/control-plane routing failure (control plane returned 200 + correct identifiers for smoked services).
3. HEAD/branch mismatch (see above) — environment mismatch vs task spec, not a runtime defect proven by this audit.
4. No CORS / timeout / mixed-content errors observed via curl. Browser-side CORS: NOT VERIFIED.

## Android / Termux connectivity result
- Loopback `127.0.0.1:8000` reachable from Termux shell: YES (all APIs 200 after Hub start).
- Hub binds `0.0.0.0:8000` per `yasinhub/api/server.py:run()`.
- Agent `127.0.0.1:8080` reachable with token auth: YES (`healthy` + `ready:true`, `platform:Android arch:aarch64 is_termux:true`).
- LAN-IP / separate-namespace browser path: NOT VERIFIED (same-device only).

## Defect in YasinHub
- No new real regression proven by this audit. No defect commit to record.
- Pre-existing FAILED services noted above are not diagnosed here; logs + process state would be needed per service.

## Verdict
- VERDICT: PARTIAL
- Reason: Termux same-device Hub API + control-plane lifecycle + PID change + agent health = PASS with real HTTP 200 evidence; real-browser Network-panel proof = NOT VERIFIED; 5 services FAILED pre-existing; HEAD/branch ≠ task spec.

## Code change
- NO CODE CHANGE
