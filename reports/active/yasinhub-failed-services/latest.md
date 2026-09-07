# YasinHub FAILED Services — Diagnosis (no fix applied)

## 1. Date/time
- UTC: 2026-09-07T04:46:18Z (status snapshot; log evidence from Hub runs 2026-09-06/07)
- Device: Android / Termux, same-device shell (no browser involved)

## 2. YasinHub HEAD
- `git rev-parse HEAD` = `435a1832b4e4ab88ae9dfd25c872a1ce5a614a66` (detached HEAD, canonical audited commit)
- `git status -sb` = `## HEAD (no branch)` + `?? yasin_hub.egg-info/` (no tracked modifications)
- Hub API live during diagnosis (PID 13058 from this HEAD)

## 3. Device/runtime
- Android aarch64, Termux, Python 3.14.6 (Hub `.venv`), `python3` on PATH
- Hub binds `0.0.0.0:8000`; children spawned via `service_manager.start_service` (no shell, `cwd=project.path`, stdout+stderr → `~/.yasinhub/logs/<service>.log`, 2s startup grace, exit code recorded in status store)

## 4. Current YasinHub status
- `GET /api/status` → HTTP 200, 8 projects:
  - RUNNING: `yasinrelay, yasin-agent, yasin-ai` (real PIDs, verified earlier)
  - FAILED: `yasinfeed (exit 2), eitaa_news_v2 (exit 2), yasin-coder (exit 1), yasinpress (exit 1), backup_manager (exit 2)`
  - All 5 FAILED have `pid: null` in `/api/metrics/<svc>` (no live process)
- Message pattern: `خطا: پروسس در حین راه‌اندازی با کد خروج <N> متوقف شد.` (Hub startup-verification contract, not an app error)

## 5. Five-service matrix

| Service | Status | Exit | Command | Root Cause | Fix Required |
|---|---|---|---|---|---|
| yasinfeed | FAILED | 2 | `python3 yasinfeed.py` (cwd `~/yasineco/Yasinfeed`) | Wrong entrypoint filename: repo has package `yasinfeed/` + console script `yasinfeed`, no top-level `yasinfeed.py` → interpreter `can't open file`, exit 2 | YES (registry wiring) |
| eitaa_news_v2 | FAILED | 2 | `python3 eitaa_news_v2.py` (cwd = Hub dir, path null) | Entrypoint script missing ecosystem-wide (find to depth 5: no `eitaa_news_v2.py`; only eitaa publisher modules inside other packages) → `can't open file`, exit 2 | YES (missing component / wrong command) |
| yasin-coder | FAILED | 1 | `python3 -m yasin_coder.cli` (cwd = Hub dir) | Module not installed/found: `ModuleNotFoundError: No module named 'yasin_coder'`; no implementation in ecosystem (only `YASIN-DOCS/.../YASIN_CODER_ARCHITECTURE.md`) → exit 1 | YES (missing component) |
| yasinpress | FAILED | 1 | `python3 -m yasinpress.cli` (cwd = Hub dir) | Module not on path: `ModuleNotFoundError: No module named 'yasinpress'`; implementation exists at `~/yasineco/YasinPress-Rewrite-/yasinpress` (with `cli/`) but registry `path: null` so Hub never adds it to `PYTHONPATH` → exit 1 | YES (registry wiring) |
| backup_manager | FAILED | 2 | `python3 backup_manager.py` (cwd = Hub dir, path null) | Wrong cwd/path: file exists only at `~/yasineco/YasinPress/backup_manager.py`, absent in Hub dir → `can't open file`, exit 2 (plus latent: it does `from config import ...`, so cwd must be YasinPress even after path fix) | YES (registry wiring) |

## 6. Detailed evidence per service

### yasinfeed (exit 2)
- EXPECTED COMMAND (registry/config): `python3 yasinfeed.py`, cwd `~/yasineco/Yasinfeed` (config file says `Yasinfeed-main`; runtime canonicalizes to `Yasinfeed` via `config_manager._canonical_project_path` stripping `-main` — resolution works, filename does not).
- ACTUAL COMMAND: same (Hub spawns argv `["python3","yasinfeed.py"]`, no shell).
- EXIT CODE: 2 (status store + matches CPython "can't open file" exit code).
- EVIDENCE: `~/.yasinhub/logs/yasinfeed.log` (×4 identical): `python3: can't open file '/data/data/com.termux/files/home/yasineco/Yasinfeed/yasinfeed.py': [Errno 2] No such file or directory`. Filesystem: `~/yasineco/Yasinfeed/` contains package dir `yasinfeed/` (with `cli/main.py`, argparse CLI), `pyproject.toml` (`[project.scripts] yasinfeed = "yasinfeed.cli.main:main"`), and NO top-level `*.py` (`ls Yasinfeed/*.py` → No such file). `~/yasineco/Yasinfeed-main` does not exist.
- FAILURE REASON: command/config error (stale entrypoint filename). NOT dependency, NOT permission (dir listable), NOT port conflict (died at exec), NOT env (never reached app code).

### eitaa_news_v2 (exit 2)
- EXPECTED COMMAND: `python3 eitaa_news_v2.py`, cwd = Hub dir (`path: null`).
- ACTUAL COMMAND: same.
- EXIT CODE: 2.
- EVIDENCE: `~/.yasinhub/logs/eitaa_news_v2.log`: `python3: can't open file '.../YasinHub/eitaa_news_v2.py': [Errno 2] No such file or directory` (two Hub generations: one `~/YasinEco/YasinHub` line from an older checkout, current `~/yasineco/YasinHub` line). Filesystem: file absent in Hub dir; `find ~/yasineco -maxdepth 5 -iname '*eitaa*'` finds only eitaa publisher *modules* inside Yasinfeed/YasinPress/YasinPress-Rewrite-/YasinRelay — no standalone `eitaa_news_v2.py`.
- FAILURE REASON: missing component / wrong command (nothing to execute). Failure occurs before application startup (interpreter cannot open script). NOT dependency/permission/port/env.

### yasin-coder (exit 1)
- EXPECTED COMMAND: `python3 -m yasin_coder.cli`, cwd = Hub dir (`path: null`).
- ACTUAL COMMAND: same.
- EXIT CODE: 1.
- EVIDENCE: `~/.yasinhub/logs/yasin-coder.log` (×3): `python3: Error while finding module specification for 'yasin_coder.cli' (ModuleNotFoundError: No module named 'yasin_coder')`. Checks: `.venv/bin/python -c "import yasin_coder"` → Traceback; `find ~/yasineco -maxdepth 4 -iname '*yasin_coder*'` → only docs architecture file. No implementation anywhere in ecosystem.
- FAILURE REASON: missing component (no runtime to wire). NOT config typo of an existing module, NOT dependency version, NOT permission/port/env.

### yasinpress (exit 1)
- EXPECTED COMMAND: `python3 -m yasinpress.cli`, cwd = Hub dir (`path: null`).
- ACTUAL COMMAND: same.
- EXIT CODE: 1.
- EVIDENCE: `~/.yasinhub/logs/yasinpress.log` (×2): `ModuleNotFoundError: No module named 'yasinpress'`. BUT implementation exists: `~/yasineco/YasinPress-Rewrite-/yasinpress/` with `__init__.py`, `cli/` (`main.py, commands.py, parser.py...`). Hub `service_manager._service_env` only prepends `project.path` to `PYTHONPATH` — with `path: null` nothing is added, and Hub venv does not contain the package (import check → Traceback).
- FAILURE REASON: service wiring error (registry `path: null` + uninstalled package). Failure at import, before app startup. NOT missing code, NOT permission/port; dependency health inside the package NOT VERIFIED (never reached).
- Note: repo dir is literally `YasinPress-Rewrite-` (trailing dash) — any future path wiring must use the exact on-disk name.

### backup_manager (exit 2)
- EXPECTED COMMAND: `python3 backup_manager.py`, cwd = Hub dir (`path: null`).
- ACTUAL COMMAND: same.
- EXIT CODE: 2.
- EVIDENCE: `~/.yasinhub/logs/backup_manager.log`: `can't open file '.../YasinHub/backup_manager.py'` (both `YasinEco` and `yasineco` Hub generations). Filesystem: absent in Hub dir; present at `~/yasineco/YasinPress/backup_manager.py` (header: YusiNews Backup Manager; sibling `config.py` exists in same dir; source does `from config import DB_PATH, DATA_DIR` → cwd-coupled import).
- FAILURE REASON: wrong cwd/path (registry `path: null`). Primary failure at exec (exit 2); secondary latent coupling (`from config import ...` requires cwd or sys.path = YasinPress dir) to address in the same fix. NOT permission (file readable), NOT port, NOT env.

## 7. Root-cause classification
- Command/config (stale entrypoint): yasinfeed.
- Missing component (no implementation in ecosystem): eitaa_news_v2, yasin-coder.
- Service wiring (`path: null` / uninstalled package): yasinpress, backup_manager (backup also cwd-coupled import).
- Ruled OUT for all five (evidence: interpreter-level stderr, death inside 2s grace, `pid: null`, no bind/port in logs): Python/runtime incompatibility, permission, port conflict, environment/secret, Control Plane defect. Dependency-missing NOT demonstrated in any case (failures precede dependency imports; yasinpress/Yasinfeed inner deps NOT VERIFIED).
- No Control Plane / API / PWA / PID-authority defect evidenced: routing, spawning, logging, exit-code capture, and PID lifecycle all behaved per contract (proven on yasin-agent/yasinrelay).
- Cross-service causation: none assumed; each service fails independently at its own exec/import step. Shared pattern (stale `path: null` + filename entries) is a registry-content issue, not a runtime cascade.

## 8. Fix candidates (NOT applied — diagnosis only)
- FIX_CANDIDATE-1 (yasinfeed): align `start_command` with the packaged entrypoint (`yasinfeed` console script / `yasinfeed.cli.main`), keeping `path: ~/yasineco/Yasinfeed`. Requires verifying the CLI's expected args and long-run behavior before wiring.
- FIX_CANDIDATE-2 (eitaa_news_v2): decide whether the bot still exists (locate canonical repo/entrypoint) or retire the registry entry; do NOT invent a script.
- FIX_CANDIDATE-3 (yasin-coder): implementation missing — either add the component or retire the entry; no registry tweak can fix this alone.
- FIX_CANDIDATE-4 (yasinpress): wire `path` to the canonical press repo (`YasinPress-Rewrite-`, exact spelling) and/or install the package so `python3 -m yasinpress.cli` resolves; verify `cli/main.py` startup contract first.
- FIX_CANDIDATE-5 (backup_manager): wire `path` to `~/yasineco/YasinPress` so both file resolution and `from config import ...` work; verify DB/data-dir requirements (presence-only) before enabling.
- Also: stale `Yasinfeed-main` in `~/.yasinhub/config.yaml` is currently masked by `-main` canonicalization — consider updating the file to `Yasinfeed` to remove drift (cosmetic, no behavior change).

## 9. Connectivity status
- PWA_CONNECTIVITY: PASS (unchanged; `GET /api/health|services|status`, `GET /dashboard/`, control POSTs all HTTP 200 on `435a183`; yasin-agent/yasinrelay/yasin-ai RUNNING with real PIDs; browser Network-panel proof remains NOT VERIFIED per audit scope).
- Service health is reported separately from connectivity; the 5 FAILED entries reflect managed-service wiring/components, not the Hub pipe.

## 10. Final verdict
- Diagnosis verdict: 5/5 root causes identified with log + filesystem evidence; 0 fixes applied.
- No new YasinHub Control Plane defect proven.

## 11. No-code-change statement
- CODE_CHANGE: NO CODE CHANGE (production repos untouched; only this Operations report file added).
- Secrets: none printed or stored (only presence-style statements; no `.env`/token/key contents, no full env dump).
