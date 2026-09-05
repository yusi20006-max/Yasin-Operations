# Checkpoint 29 — Final Regression — Issue #174

**Status:** PASS (all suites, security, no fabrications)
**Date/time:** 2026-09-05 05:30 UTC
**Device:** Samsung SM-A705FN Android 11 API30 aarch64 Termux Python 3.14.6 (real)
**Repositories:** yasineco/YasinHub c7ca808 fix/final-device-acceptance-174, yasineco/YasinRelay 6bbe6d4 main, yasineco/Yasin-agent 44c130a main, yasineco/Yasin-AI 410214d main
**Commits:** c7ca808 (5965c64 parent), 6bbe6d4, 44c130a, 410214d

## Objective
After all changes, run complete suites for Hub, Agent, Relay, AI on actual device, verify expected baselines, no collection errors, no skipped to hide cryptography problem, and security regression checks.

## YasinHub — Complete Suite

**Command:** `.venv/bin/python -m pytest tests -q` (canonical venv, system fallback also 478)
**Workdir:** `yasineco/YasinHub`
**Python:** 3.14.6 Clang 21.0.0 aarch64 Android 11 (via .venv python3.14)
**Result:** **478 passed** 0 failed 0 errors 42.60s (also system python 478 passed 42.71s)
**Expected baseline:** 478 passed 0 failed → **MATCH**
**Test count change:** none (471/7 → 478/0 fix already in c7ca808, now stable)
**Evidence:** `478 passed in 42.60s` tail output, earlier 40.28s same.

**Command variant:** `python -m pytest tests -q` (system) also 478 passed — same.

## Yasin-agent — Complete Suite

**Command:** `.venv/bin/python -m pytest tests -q`
**Workdir:** `yasineco/Yasin-agent`
**Python:** 3.14.6 (venv)
**Result:** **240 passed** 0 failed 2 warnings (StarletteDeprecation) 11.36s
**Expected baseline:** 240 passed 0 failed → **MATCH**
**Note:** `python -m pytest tests -q` (system) gives 194 passed 3 skipped because `fastapi/uvicorn` test-server deps only in venv and `httpx` missing. Canonical is `.venv` as used in CI, so 240 is authoritative. No test count change explanation needed beyond venv vs system; earlier 240 via venv matches.

**Failure output:** none.

## YasinRelay — Complete Suite

**Command:** `.venv/bin/python -m pytest tests -q`
**Workdir:** `yasineco/YasinRelay`
**Python:** 3.14.6 (venv, has `requests`)
**Result:** **108 passed** 0 failed 2.71s
**Expected baseline:** 108 passed 0 failed → **MATCH**
**Command variant:** `python -m pytest tests -q` (system) fails 11 collection errors `ModuleNotFoundError: requests` — expected, venv is canonical per `scripts/install_termux.sh` using `.venv` with deps.

**Failure output:** none in venv.

## Yasin-AI — Complete Suite on Actual Device

**Command:** `python -m pytest tests -q` (system python with `--system-site-packages` to include `python-cryptography` 50.0.1 abi3)
**Workdir:** `yasineco/Yasin-AI`
**Python:** 3.14.6 Clang 21.0.0 aarch64 Android 11
**Architecture:** aarch64
**Dependency version:** cryptography 50.0.1 (abi3.so) cffi 2.1.1 yasinai 1.1.4
**Result:** **415 passed** 0 failed 0 errors ~31s (also `pytest --collect-only -q` 415 tests collected 0.80s)
**Also tested:** `python -c "import cryptography.hazmat.bindings._rust; print('ok')"` → ok, `pip show cryptography` 50.0.1
**Expected:** No collection errors, no skipped to hide cryptography problem → **PASS** (0 collection errors, 0 skipped hiding problem)
**Venv variant:** `.venv/bin/python -m pytest tests -q` fails 38 collection errors (missing system-site-packages) — expected per `install_termux.sh` docs: use system python with `--system-site-packages`. Canonical for AI on Termux is system python.
**Failures:** none.

## Security Regression Verification

| Check | Expected | Actual | Verdict |
|-------|----------|--------|---------|
| subprocess execution remains `shell=False` | yes | `yasinhub/service_manager.py:207 shell=False` `service_manager.py:288 shell=False` + `shlex.split` at `_command_argv` `shlex.split(command, posix=True)` | PASS |
| no shell injection regression | no `shell=True` in Hub control | `grep -rn shell=True yasinhub --include=*.py` only pip internal, no Hub control | PASS |
| PID identity validation active | yes via `is_pid_alive` | `yasinhub/pid_store.py:42-61` `os.waitpid(pid, WNOHANG)` + `os.kill(pid,0)` + callers `service_manager:31 _is_pid_alive`, `report:81 build_report`, `api/server:365` | PASS |
| zombie detection active | yes via `waitpid(WNOHANG)` | `pid_store:is_pid_alive` handles zombie `pid_reaped == pid → False`, tested dummy 18269 kill → False, yasinrelay empty exit 1 → False | PASS |
| no secrets in logs | redacted | `yasinrelay/logging_config.py:24-27` replaces `EITAA_TOKEN→[EITAA_TOKEN_REDACTED]` `AI_API_KEY→[AI_API_KEY_REDACTED]`, Hub logs contain only `هیچ کانال منبعی تنظیم نشده` etc, `~/.yasinhub/logs/yasinrelay.log` no tokens | PASS |
| `.env` not committed | yes | `.gitignore` has `.env` `!.env.example`, `git -C YasinRelay status --short` clean, `git -C YasinHub status` only `yasin_hub.egg-info/`, `.env` 907B 0600 not tracked | PASS |
| failed startup removes stale PID | yes | `service_manager.py:223 remove_pid`, `228 write_status success=False`, `245 remove_pid`, verified `read_pid('yasinrelay')=None` after empty start | PASS |
| failed startup cannot report RUNNING | yes | `report.py:calculate_health_state` `process_running==False && last_success==False → FAILED` not RUNNING, verified `health_state=FAILED` | PASS |
| Hub remains sole lifecycle authority | yes | `registry.py:62` single `.venv/bin/yasinrelay-termux run --schedule --non-interactive` via `service_manager.start_service`, no second Control Plane found `grep -rn Control Plane` only Hub | PASS |

No security regression introduced.

## Additional Checks

- No secrets appear in test outputs or reports (only present/absent, len, no values)
- Zombie defect fix commit c7ca808 still intact: `service_manager.py:217-252` 2.0s poll interval 0.15s, verified again `success=False` for empty config
- No weakening or skipping tests to get green: all suites run full, AI 415 not skipped, cryptography tests not disabled
- No `.env` secrets committed: `git diff --cached` empty for `.env`

## Blockers
- None for regression. All expected baselines MATCH when using canonical runners (.venv for Hub/Agent/Relay, system for AI with system-site-packages).

## Next Action
Checkpoint 30 — Final Acceptance (truthful FULL PASS vs PARTIAL decision, final report rewrite).

## Evidence
- Hub: `.venv/bin/python -m pytest tests -q → 478 passed in 42.60s`
- Agent: `.venv/bin/python -m pytest tests -q → 240 passed`
- Relay: `.venv/bin/python -m pytest tests -q → 108 passed`
- AI: `python -m pytest tests --collect-only -q → 415 tests collected` + `python -m pytest tests -q → 415 passed in 31.32s` + `python -c import cryptography → 50.0.1 ok`
- Security: `grep -rn shell=False`, `grep -rn is_pid_alive`, `cat pid_store.py`, `cat logging_config.py`, `git status --short`, `cat .gitignore`
- Device: `python -V 3.14.6`, `platform.machine aarch64`, `cryptography 50.0.1 abi3.so`

## Commands Executed (exact)
```
# Hub
workdir yasineco/YasinHub .venv/bin/python -m pytest tests -q  → 478 passed 42.60s
# Agent
workdir yasineco/Yasin-agent .venv/bin/python -m pytest tests -q → 240 passed 11.36s
workdir yasineco/Yasin-agent python -m pytest tests --collect-only -q → 194 collected (system w/o server deps)
# Relay
workdir yasineco/YasinRelay .venv/bin/python -m pytest tests -q → 108 passed 2.71s
# AI
workdir yasineco/Yasin-AI python -m pytest tests --collect-only -q → 415 collected 0.80s
workdir yasineco/Yasin-AI python -m pytest tests -q → 415 passed 31.32s
python -c "import cryptography; print(cryptography.__version__)" → 50.0.1
pip show cryptography
grep -rn shell=False yasineco/YasinHub
grep -rn is_pid_alive yasineco/YasinHub
cat yasineco/YasinHub/yasinhub/pid_store.py
cat yasineco/YasinHub/.gitignore
git -C yasineco/YasinRelay status --short
cat yasineco/YasinRelay/yasinrelay/logging_config.py
```
