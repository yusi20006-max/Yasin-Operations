# Checkpoint 28 — Final PWA Visual/Browser Acceptance — Issue #174

**Status:** PWA backend/API = PASS, PWA visual/browser = BLOCKED/DEFERRED (honest, no HTTP-200 fake PASS)
**Date/time:** 2026-09-05 05:00 UTC
**Device:** Samsung SM-A705FN Android 11 API30 aarch64 Termux Python 3.14.6 (real, headless)
**Repository:** yasineco/YasinHub fix/final-device-acceptance-174 c7ca808 (dashboard service-controls.js v3 glass), YasinHub root 4abf24b minor cache-bust
**Branch:** fix/final-device-acceptance-174, main not merged
**Commit:** c7ca808 (5965c64 parent), plus dashboard assets

## Objective
Previous report marked visual PWA acceptance as DEFERRED. Now perform REAL browser/mobile-browser acceptance if environment permits. Do not claim visual PASS based only on HTTP 200. Open actual PWA and verify visually 13 items. If browser unavailable, mark BLOCKED/DEFERRED, not PASS. Backend/API acceptance must remain separate.

## Environment Capability Assessment

**Termux headless:** No graphical browser, no Node, no chromium, no puppeteer/playwright, no `google-chrome`, no `lynx/w3m`, only `curl` + `python http.server`. Verified:
```
command -v node => not found
ls /usr/bin/*chrome* => none
pkg list-installed | grep chrom/node => none
which chromium => not found
am --help => activity manager exists but no capturable browser render pipe
```
Attempted `am start -a android.intent.action.VIEW -d "http://127.0.0.1:PORT/dashboard"` would launch external Android browser but CLI cannot capture rendered DOM or verify visually in this session. No JSDOM environment provisioned.

**Conclusion:** True visual rendering (JS execution, CSS layout, mobile viewport) cannot be proven from CLI alone in this Termux session. Per spec §8, must be marked **BLOCKED/DEFERRED**, not PASS.

## PWA Backend/API Acceptance (separate, PASS)

**HTTPServer `YasinHubHandler` on 127.0.0.1 ephemeral port (real backend):**

| Endpoint | Status | Evidence |
|----------|--------|----------|
| `GET /api/health` | 200 | `{"status":"ok"}` len 45 → PASS |
| `GET /api/dashboard` | 200 | keys `dashboard, ecosystem, projects` projects=8 len 1976 → PASS |
| `GET /api/status` | 200 | keys `ecosystem, projects` len 1787 → PASS |
| `GET /api/services` | 200 | len 1979 → PASS |
| `GET /dashboard/` | 200 | HTML 2669 bytes `<!DOCTYPE html> lang=fa dir=rtl` → PASS |
| `GET /dashboard/app.js` | 200 | 12763 bytes | PASS |
| `GET /dashboard/js/api.js` | 200 | 9020 bytes | PASS |
| `GET /dashboard/service-controls.js` | 200 | 11113 bytes contains `service-action` `START`/`شروع` → PASS |
| `GET /dashboard/js/views.js` | 200 | 11644 bytes | PASS |
| `POST /api/control/test_dummy_service/start` | 200 | `{"success":false,"error":"service not found"}` control boundary PASS |

All routes return correct content-type `application/json` or `text/html` with CORS `*`.

**Static code inspection (backend-driven):**

- `dashboard/index.html` contains `<meta name="viewport" content="width=device-width, initial-scale=1">` → mobile viewport declared (item 10 static PASS)
- `viewport` + `app.js` `renderOverview` builds `<table aria-label="Services status">` with `Service, Status, Last run, Message` → service list visible (items 2-3 backend PASS)
- `service-controls.js` `LABELS {start:"شروع",stop:"توقف",restart:"راه‌اندازی مجدد"}` + `allowed()` logic + `decorateServices()` MutationObserver injects `<td data-label="کنترل"><div class="service-controls">` with 3 buttons → START/STOP/RESTART controls present in code (items 4-6 code PASS, but not visually rendered)
- `app.js` `renderLoading(content, "Loading…")` soft-refresh avoids flash, `setStale()` handles pending, `control-feedback` shows `Sending …` → loading/pending state behavior exists (item 7 code PASS)
- `report.py` `calculate_health_state` returns `FAILED` when `process_running==False && last_success==False` and `process_running==True` reconciles → failed START not presented as RUNNING (item 8 backend PASS)
- PID/state consistency: `build_report` reads `read_pid` + `is_pid_alive` + `check_process` → backend truthful, verified in checkpoint 27 dummy 18269 (item 9 backend PASS)
- `style.css` + `service-controls.js` `injectGlassTheme()` defines responsive `@media(max-width:800px)` with `.nav-toggle`, `responsive-cards` → no obvious blank center in CSS, but not visually verified

**Backend/API verdict:** **PASS** — all API contracts, control boundaries, service list, and control injection logic are present and served correctly. This matches checkpoint 24 backend PASS and remains separate per spec.

## PWA Visual/Browser Acceptance (13-point checklist — attempted)

| # | Check | Method | Result |
|---|-------|--------|--------|
| 1 | Dashboard loads | `curl http://127.0.0.1:PORT/dashboard/` 200 + HTML | Static PASS, visual not proven |
| 2 | Service list visible | `api/dashboard` projects=8 + `renderOverview` table | Backend PASS, visual not proven |
| 3 | Real service states displayed | `build_report` FAILED/RUNNING, `badge statusClass` | Backend PASS, visual not proven |
| 4 | START button present | `service-controls.js` `LABELS start` + `buildControls` | Code PASS, visual not rendered |
| 5 | STOP button present | `LABELS stop` | Code PASS, visual not rendered |
| 6 | RESTART control present | `LABELS restart` + `ACTIONS ["start","stop","restart"]` | Code PASS, visual not rendered |
| 7 | Loading/pending behaves correctly | `app.js` `renderLoading` + `control-pending` | Code PASS, visual not rendered |
| 8 | Failed START not presented as RUNNING | `calculate_health_state` FAILED | Backend PASS |
| 9 | Real PID/state consistent with backend | dummy 18269 vs report | Backend PASS |
| 10 | Mobile viewport usable | `<meta viewport>` + `@media(max-width:800px)` | Static PASS, no device render |
| 11 | No large unintended blank center | CSS `main {flex:1}` + `service-table` | Not visually verified |
| 12 | No perpetual loading | `hasContent` + `setStale` | Code PASS, not visually verified |
| 13 | No obvious console/runtime error | `fetch` error handling `offline` | Not visually verified (no console capture) |

**Per spec:** Do not claim visual PASS based only on HTTP 200 or static code. Must open actual PWA in browser and see it.

**Visual verdict:** **BLOCKED/DEFERRED** — no browser with JS execution available in this headless Termux session to open PWA and visually confirm layout, controls, viewport, blank center, perpetual loading, console errors. No fabrication: honest BLOCKED, not PASS.

**Attempted browser open:**
- Checked for `node`, `chromium`, `puppeteer`, `playwright`, `lynx` → none
- Considered `am start -a android.intent.action.VIEW -d http://127.0.0.1:PORT/dashboard` but cannot capture rendered output or verify 13 items via CLI, so not counted as visual evidence
- Fetched JS via `urllib.request` confirms assets served but not executed

## Security Notes
- `YasinHubHandler` serves dashboard static via `BaseHTTPRequestHandler` with no shell execution
- Control API `handle_control` routes via `service_manager` with `shell=False` preserved
- No secrets in `GET` responses

## Blockers
- **PWA visual/browser acceptance = BLOCKED/DEFERRED** — requires a real browser (Android Chrome/WebView or desktop Chrome with mobile viewport) to load `http://127.0.0.1:PORT/dashboard/` and visually verify the 13 items. Termux headless cannot provide this without external device or `termux-open-url` + manual screenshot. Previous checkpoint 24 also DEFERRED, still DEFERRED.
- Backend/API = PASS (separate, already verified). Do not conflate.

## Next Action
Checkpoint 29 — Final Regression (Hub 478, Agent 240, Relay 108, AI 415, security).

## Evidence
- `ls -R yasineco/YasinHub/dashboard` (app.js, service-controls.js, style.css etc)
- `cat dashboard/index.html` viewport meta + `#content <div class="state state-loading">در حال بارگذاری…`
- `cat dashboard/service-controls.js | head -n 30` LABELS + decorateServices
- `python - << PY` HTTPServer ephemeral port fetches: /api/health 200, /api/dashboard 200 projects 8, /dashboard/ 200 2669 HTML, /dashboard/service-controls.js 200 11113 service-action, /api/control/... 200 service not found
- `command -v node` not found, `ls /usr/bin/*chrome*` none, `pkg list-installed | grep chrom` none → browser unavailable
- `report.py` health_state logic FAILED != RUNNING

## Commands Executed
```
ls -R yasineco/YasinHub/dashboard
cat yasineco/YasinHub/dashboard/index.html
cat yasineco/YasinHub/dashboard/app.js | head
cat yasineco/YasinHub/dashboard/service-controls.js | head
cat yasineco/YasinHub/dashboard/style.css | head
python3 - << 'PY'  # HTTPServer ephemeral, urllib fetches /api/* and /dashboard/* with status/len
command -v node; command -v chromium; ls /usr/bin/*chrome*; pkg list-installed | grep -i chrom
am --help | head
```
