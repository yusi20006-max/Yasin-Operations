# YasinHub Service Registry / Canonical Entrypoint Audit — latest

## Audit scope
- DIAGNOSIS ONLY. No production code changed, no registry entry added/removed/modified, no service created, no fake executable/wrapper created.
- All 8 YasinHub registry entries audited against canonical ecosystem repositories (read-only inspection): yasinrelay, yasin-agent, yasin-ai, yasinfeed, yasinpress, eitaa_news_v2, yasin-coder, backup_manager.
- Cross-repo sources inspected: YasinHub, Yasinfeed, YasinPress-Rewrite-, YasinRelay, Yasin-agent, Yasin-AI, Yasin-cli, Yasin-core, YasinPress (backup owner), YASIN-DOCS.
- Failure evidence reused from prior diagnosis (`~/.yasinhub/logs/<service>.log` + `/api/metrics` pid null + status store exit codes); root causes re-confirmed, not re-executed.
- Secrets: none recorded (presence-style only; no `.env`/token/key contents, no env dump).

## YasinHub HEAD
- `435a1832b4e4ab88ae9dfd25c872a1ce5a614a66` (detached HEAD, canonical audited commit)
- Registry source: `yasinhub/registry.py:40-97`; effective runtime config via `yasinhub/config_manager.py:151-197` (`-main` suffix canonicalization); spawn contract `yasinhub/service_manager.py` (`shell=False`, `cwd=project.path`, `PYTHONPATH+=project.path`, log capture, 2s startup grace, exit-code status).

## Registry matrix

| Service | Canonical Repo | Implementation | Entrypoint | Canonical Command | Registry Match | Hub Managed? | Action |
|---|---|---|---|---|---|---|---|
| yasinrelay | YasinRelay | YES (RUNNING, PID-proven) | `.venv/bin/yasinrelay-termux` → `python -m yasinrelay.cli` | `.venv/bin/yasinrelay-termux run --schedule --non-interactive`, cwd `~/yasineco/YasinRelay` | YES | YES | none |
| yasin-agent | Yasin-agent | YES (RUNNING, PID-proven) | `agent_platform.server` package (`server/__main__.py`) | `.venv/bin/python -m agent_platform.server`, cwd `~/yasineco/Yasin-agent` (+ service token via Hub) | YES | YES | none |
| yasin-ai | Yasin-AI | YES (RUNNING, PID-proven) | `yasinai.cli` (`main.py` has serve) / script `yasin` | `yasin serve`, cwd `~/yasineco/Yasin-AI` | YES | YES | none |
| yasinfeed | Yasinfeed | YES (package `yasinfeed/` + `cli/main.py` + `main.py`) | `python -m yasinfeed.main` (README "Run YasinFeed"; engine + signal handlers = daemon-suitable) / script `yasinfeed` | `python -m yasinfeed.main`, cwd `~/yasineco/Yasinfeed`, req `feedparser,PyYAML` (absent in Hub venv — secondary) | NO (`python3 yasinfeed.py`, file absent) | YES (once wired) | WIRING_FIX |
| yasinpress | YasinPress-Rewrite- | YES (package `yasinpress/` + `cli/`, script `yasinpress`, req py>=3.13; Hub py 3.14 OK) | `yasinpress.cli.main:main`, subcommands `status,version,config,health,run`; `run` = daemon tick loop (see semantics) | `yasinpress run`, cwd repo root (`.env` discovery + `pythonpath ["."]`; pkg not in Hub venv) | NO (`path:null`, module unresolvable) | CONDITIONAL (daemon-capable; unattended only with stdin=EOF + env presets — see semantics) | WIRING_FIX + precondition |
| eitaa_news_v2 | — | CANONICAL_IMPLEMENTATION: NOT FOUND (exhaustive find over `~/yasineco` + `~/YasinEco`; only eitaa modules inside other packages; Hub refs are tests with `/dummy/path`) | none | none | NO | NO | STALE → retirement candidate (no delete applied) |
| yasin-coder | — | CANONICAL_IMPLEMENTATION: NOT FOUND (no package anywhere; only `YASIN-DOCS/.../YASIN_CODER_ARCHITECTURE.md`, self-described planned expansion; zero refs outside Hub registry) | none | none | NO | NO | STALE → retirement candidate (no fake executable) |
| backup_manager | YasinPress (`backup_manager.py`, 56 lines) | File YES; service contract NO (no `__main__` guard, no loop — one-shot class method; would exit 0 instantly and fail Hub grace) | none | N/A (one-shot; `from config import DB_PATH/DATA_DIR` cwd-coupled to YasinPress, `DATA_DIR=BASE_DIR/"data"`, `DB_PATH=DATA_DIR/"news.db"`) | NO (`path:null`, file absent in Hub cwd → exit 2) | NO (one-shot utility, not a Hub service) | Re-home decision (retire from registry or external scheduler; NOT daemonized per rules) |

## Root causes (FAILED entries)
- yasinfeed (exit 2): stale entrypoint filename. Log: `can't open file '.../Yasinfeed/yasinfeed.py'`. Filesystem: no top-level `*.py`; package + documented launcher exist.
- eitaa_news_v2 (exit 2): missing component. Log: `can't open file '.../YasinHub/eitaa_news_v2.py'`. Nothing to execute anywhere.
- yasin-coder (exit 1): missing component. Log: `No module named 'yasin_coder'`. Docs-only product.
- yasinpress (exit 1): wiring. Log: `No module named 'yasinpress'`. Code exists but unreachable (`path:null`, uninstalled).
- backup_manager (exit 2): wrong category + wiring. Log: `can't open file '.../YasinHub/backup_manager.py'`. One-shot file in another repo; can never satisfy long-running contract.

## Evidence paths
- `~/yasineco/YasinHub/yasinhub/registry.py:40-97`, `~/yasineco/YasinHub/yasinhub/config_manager.py:151-197`
- `~/yasineco/Yasinfeed/README.md` (Run section), `~/yasineco/Yasinfeed/yasinfeed/main.py`, `~/yasineco/Yasinfeed/pyproject.toml` (`[project.scripts]`)
- `~/yasineco/YasinPress-Rewrite-/pyproject.toml` (script `yasinpress`, `requires-python>=3.13`), `~/yasineco/YasinPress-Rewrite-/yasinpress/cli/main.py:55-170`, `~/yasineco/YasinPress-Rewrite-/yasinpress/cli/parser.py:17`, `~/yasineco/YasinPress-Rewrite-/yasinpress/runtime.py:40-56`, `~/yasineco/YasinPress-Rewrite-/yasinpress/runtime_factory.py`
- `~/yasineco/YasinRelay/.venv/bin/yasinrelay-termux` (contract header), `~/yasineco/Yasin-agent/agent_platform/server/`, `~/yasineco/Yasin-AI/yasinai/cli/main.py`
- `~/yasineco/YasinPress/backup_manager.py` (56 lines), `~/yasineco/YasinPress/config.py:127,139`
- `~/yasineco/YASIN-DOCS/docs/architecture/YASIN_CODER_ARCHITECTURE.md`
- `~/.yasinhub/logs/{yasinfeed,eitaa_news_v2,yasin-coder,yasinpress,backup_manager}.log`

## `yasinpress run` semantics
- `cli/main.py:155`: `run` → `_startup_channel_setup()` + `_startup_feed_setup()` → `build_runtime()` → `Runtime.run()`.
- `runtime.py:40-56`: `while not _stop: tick(); wait(interval)` — long-running daemon loop ("YasinPress is active"), exits only on external stop. **DAEMON, not one-shot.**
- Interactive code in `run` path (`main.py:61-68,123-130`): `getpass`/`input()` (Persian prompts, `.env` read/write at cwd-relative `Path(".env")`), all guarded by `except (EOFError, KeyboardInterrupt)` → empty-string fallback to env/saved values.
- Unattended verdict: compatible with Hub `shell=False` spawn **iff stdin=EOF** (fallbacks trigger instantly, env presets `YASINPRESS_EITAA_TOKEN/CHANNEL`, `YASINPRESS_FEEDS` apply) **and** package resolvable + cwd=repo root. If stdin is a live terminal, prompts block (false-healthy risk: process alive, stuck at prompt). `_startup_feed_setup` also probes network feeds at startup (non-fatal on failure, needs internet).
- Canonical: `yasinpress run`, cwd `~/yasineco/YasinPress-Rewrite-` (exact on-disk spelling; dir has trailing dash).
- **YASINPRESS_RUN: DAEMON** (loop proven; interactive risk mitigated only under the stated preconditions).

## Final verdict
- REGISTRY_CONTRACT_VERDICT: PASS (spawn/grace/exit-capture/PID/logging all per contract; failures are registry-content, not Control Plane defects).
- Canonical and correctly wired: yasinrelay, yasin-agent, yasin-ai.
- yasinfeed: wiring/entrypoint fix required.
- yasinpress: wiring/path fix required; daemon semantics established (DAEMON) with unattended preconditions (stdin=EOF, env presets, cwd=repo root, package resolvable).
- eitaa_news_v2: stale entry / canonical implementation not found.
- yasin-coder: stale entry / canonical implementation not found.
- backup_manager: one-shot utility, not a long-running Hub service.

## Recommended next actions (not applied)
1. yasinfeed: rewire `start_command` to `python -m yasinfeed.main` (or installed `yasinfeed` script), keep path; ensure `feedparser/PyYAML` available to the child runtime; verify long-run behavior.
2. yasinpress: wire `path` to `YasinPress-Rewrite-` + make package importable; preset Eitaa/feed env (presence-only) and guarantee stdin=EOF for Hub-spawned runs; verify `run` stays resident.
3. Decide fate of eitaa_news_v2 / yasin-coder (retire entries vs implement components) — product decision, no action taken.
4. Decide backup_manager home (remove from Hub registry vs external scheduler) — do NOT daemonize per audit rules.
5. Optional hygiene: update stale `Yasinfeed-main` in `~/.yasinhub/config.yaml` to `Yasinfeed` (currently masked by canonicalization; no behavior change).

## No-code-change statement
- CODE_CHANGE: NO CODE CHANGE (production repos untouched; registry intact; only this Operations report added).
