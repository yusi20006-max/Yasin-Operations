# Lifecycle Acceptance — Evidence

All lifecycle operations via `PYTHONPATH=. python -m yasinhub.cli <start|stop|restart|status>` with
`YASIN_ECOSYSTEM_ROOT="$HOME/YasinEco"`, CWD `~/YasinEco/YasinHub` (YasinHub `21e3060`).
PID liveness via `/proc/<pid>/cmdline`; pattern checks via `pgrep -f "[x]pattern"` (bracket form
avoids self-match). No secrets recorded. Times UTC 2026-09-05.

## Baseline (pre-task)

- `status`: yasinrelay RUNNING; yasinfeed, eitaa_news_v2, yasin-agent, yasin-ai, yasin-coder,
  yasinpress, backup_manager IDLE/STOPPED.
- `~/.yasinhub/pids/yasinrelay.pid` = 4211, alive, cmdline
  `.../yasineco/YasinRelay/.venv/bin/python -m yasinrelay.cli run --schedule --non-interactive`
  (matches pattern `yasinrelay.cli`).
- No other pid files for registry services.
- Note: one combined-pattern `pgrep -f` probe command transiently self-matched and created fake
  pid files (PID 17346) for 7 services; the next Hub `status` auto-reconciled and removed them
  (recovery mechanism works; no manual kill used).

## Registry (8 entries)

- yasinfeed: path `.../yasineco/Yasinfeed` exists; `start_command="python3 yasinfeed.py"`;
  top-level `yasinfeed.py` MISSING (package only) → BLOCKED.
- eitaa_news_v2: no path; `eitaa_news_v2.py` not found under `~/YasinEco` (maxdepth 3) → NOT_ELIGIBLE.
- yasinrelay: path exists; launcher `.venv/bin/yasinrelay-termux` exists → ELIGIBLE.
- yasin-agent: path exists; `.venv/bin/python -m agent_platform.server` exists → ELIGIBLE.
- yasin-ai: path exists; `yasin serve` resolvable (`/usr/bin/yasin`) → ELIGIBLE (with identity caveat below).
- yasin-coder: no path; `import yasin_coder.cli` → ModuleNotFoundError → NOT_ELIGIBLE.
- yasinpress: no path; `yasinpress` module not installed → NOT_ELIGIBLE.
- backup_manager: no path; top-level `backup_manager.py` absent (only under `YasinPress/` subdir) → NOT_ELIGIBLE.

## yasinrelay — PASS (START/STOP/RESTART)

- Initial: RUNNING, PID 4211, alive, identity matches `yasinrelay.cli`.
- START `start yasinrelay` → exit 0, "already running with 4211". Status RUNNING. PID 4211 alive. START=PASS.
- STOP `stop yasinrelay` → exit 0, "stopped 4211". Status IDLE/`stopped`. pid file removed.
  `/proc/4211/cmdline` absent; `pgrep -f "[y]asinrelay[.]cli"` empty (exit 1). STOP=PASS.
- RESTART `restart yasinrelay` (old 4211 dead) → exit 0, "started in background". Status RUNNING.
  New PID 17901, alive, cmdline `.../.venv/bin/python -m yasinrelay.cli run --schedule --non-interactive`,
  `17901 != 4211`, stable after 3s; still alive at later audit. RESTART=PASS.

## yasin-agent — PASS (START/STOP/RESTART)

- Initial: IDLE, no pid file, no `agent_platform.server` process.
- START `start yasin-agent` → exit 0, "started in background". Status RUNNING/`observed running`.
  New PID 18087, alive, cmdline `.venv/bin/python -m agent_platform.server`
  (matches pattern), stable after 3s. START=PASS.
- STOP `stop yasin-agent` → exit 0, "stopped 18087". Status IDLE/`stopped`. pid file removed.
  `/proc/18087/cmdline` absent; `pgrep -f "[a]gent_platform[.]server"` empty. STOP=PASS.
- RESTART `restart yasin-agent` (old 18087 dead) → exit 0, "started in background". Status RUNNING.
  New PID 20523, alive, cmdline `.venv/bin/python -m agent_platform.server`,
  `20523 != 18087`; still alive at later audit. RESTART=PASS.

## yasin-ai — FAIL (STOP refused; orphan disowned)

- Initial: IDLE, no pid file.
- START `start yasin-ai` → exit 0, "started in background". Status RUNNING/`observed running`.
  New PID 27148, alive, stable after 3s, cmdline
  `/data/data/com.termux/files/usr/bin/python /data/data/com.termux/files/usr/bin/yasin serve`.
  `yasin serve` entrypoint is `yasinai.cli.security_entrypoint:main` (not the registered discovery
  pattern `yasinai.cli.main serve`), so the registered pattern is stale; Hub
  `verify_process_identity(27148, pattern, "yasin serve")` returns False. START recorded as
  PASS with this caveat (owned Hub-spawned child, correct CWD/command, alive+stable).
- STOP `stop yasin-ai` → exit 1: "PID 27148 does not belong to yasin-ai; will not kill"
  (ownership protection). pid file removed; status reports IDLE while **27148 is still alive**
  (verified `/proc/27148/cmdline` present). STOP=FAIL; state/process inconsistent.
- RESTART: NOT ATTEMPTED → BLOCKED (STOP preconditions unmet; a Hub restart would spawn a second
  `yasin serve` and orphan the first). Orphan 27148 left running (manual kill prohibited).
  Fix required: update registry `process_pattern` to match the real runtime
  (e.g. `yasin serve` / `security_entrypoint`) or launch via `python -m ...` so argv[0] verifies.

## yasinfeed — BLOCKED (stale start_command)

- START `start yasinfeed` (single attempt, no retry — not transient) → exit 1,
  "stopped during startup verification with exit code 2". Status FAILED with same message.
  Log `~/.yasinhub/logs/yasinfeed.log` tail:
  `python3: can't open file '.../yasineco/Yasinfeed/yasinfeed.py': [Errno 2] No such file or directory`.
  No PID created. STOP/RESTART not applicable. Verdict: BLOCKED (config/stale entrypoint).

## NOT_ELIGIBLE (no lifecycle operations attempted)

- eitaa_news_v2: no runtime path/file — observer/config entry.
- yasin-coder: no path; module not installed.
- yasinpress: no path; module not installed.
- backup_manager: no path; no top-level entrypoint as configured.

## Regression (relevant existing tests only)

- `python -m pytest tests/test_service_manager_security.py tests/test_service_management_ops.py
  tests/test_stop_status_reconcile.py tests/test_supervised_status_reconcile.py
  tests/test_control_plane_startup.py tests/test_control_plane_policies.py -q`
  → **28 passed** in ~23s. No new venv, no installs, no arch changes.

## Security

- All operations through YasinHub CLI only; no shell bypass; no direct Relay launch.
- No secrets/tokens/keys recorded; no `.env` touched or committed.
- PWA untouched; no visual testing; no real publish.
